#!/usr/bin/env python3
"""
Upload DICOM files to MinIO cluster across all 5 nodes
"""

import boto3
import os
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# MinIO endpoints for all 5 nodes
NODE_ENDPOINTS = [
    ("node1", "http://localhost:9101"),
    ("node2", "http://localhost:9102"),
    ("node3", "http://localhost:9103"),
    ("node4", "http://localhost:9104"),
    ("node5", "http://localhost:9105"),
]

ACCESS_KEY = 'minioadmin'
SECRET_KEY = 'minioadmin123'
BUCKET_NAME = 'dicom-images'

# Statistics
upload_stats = {
    "total": 0,
    "success": 0,
    "failed": 0,
    "bytes": 0,
    "latencies": []
}
stats_lock = threading.Lock()

def create_bucket_if_not_exists(client, bucket):
    """Create bucket if it doesn't exist"""
    try:
        client.create_bucket(Bucket=bucket)
        print(f"   ✅ Created bucket: {bucket}")
    except:
        print(f"   ✅ Bucket already exists: {bucket}")

def upload_to_node(node_name, endpoint, files, prefix=""):
    """Upload files to a specific MinIO node"""
    try:
        client = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY,
            use_ssl=False
        )
        
        create_bucket_if_not_exists(client, BUCKET_NAME)
        
        for file_path in files:
            try:
                key = f"{prefix}/{file_path.name}" if prefix else file_path.name
                file_size = file_path.stat().st_size
                
                start = time.perf_counter()
                client.upload_file(str(file_path), BUCKET_NAME, key)
                latency = (time.perf_counter() - start) * 1000
                
                with stats_lock:
                    upload_stats["success"] += 1
                    upload_stats["bytes"] += file_size
                    upload_stats["latencies"].append(latency)
                    if upload_stats["success"] % 50 == 0:
                        print(f"   [{node_name}] Uploaded {upload_stats['success']} files (last: {latency:.1f}ms)")
                        
            except Exception as e:
                with stats_lock:
                    upload_stats["failed"] += 1
                print(f"   ❌ [{node_name}] Failed: {file_path.name} - {e}")
                
    except Exception as e:
        print(f"   ❌ Cannot connect to {node_name}: {e}")

def upload_files_to_cluster(file_dir, prefix="dicom", max_workers=20):
    """Distribute files across all 5 MinIO nodes"""
    
    # Get all DICOM files
    dicom_files = list(Path(file_dir).glob("*.dcm"))
    total_files = len(dicom_files)
    print(f"\n📁 Found {total_files} DICOM files in {file_dir}")
    
    # Distribute files evenly across nodes
    files_per_node = total_files // len(NODE_ENDPOINTS)
    node_files = []
    for i, (node_name, _) in enumerate(NODE_ENDPOINTS):
        start_idx = i * files_per_node
        end_idx = start_idx + files_per_node if i < len(NODE_ENDPOINTS) - 1 else total_files
        node_files.append((node_name, dicom_files[start_idx:end_idx]))
    
    # Upload in parallel to all nodes
    print(f"\n📤 Uploading to {len(NODE_ENDPOINTS)} MinIO nodes...")
    print("=" * 60)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for node_name, files in node_files:
            if files:
                future = executor.submit(upload_to_node, node_name, 
                                        dict(NODE_ENDPOINTS)[node_name], 
                                        files, f"{prefix}/{node_name}")
                futures.append(future)
        
        # Wait for all to complete
        for future in as_completed(futures):
            future.result()
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 UPLOAD SUMMARY")
    print("=" * 60)
    print(f"   Total files: {upload_stats['total']}")
    print(f"   Successful: {upload_stats['success']}")
    print(f"   Failed: {upload_stats['failed']}")
    print(f"   Total data: {upload_stats['bytes'] / (1024**2):.2f} MB")
    
    if upload_stats['latencies']:
        import statistics
        print(f"   Average latency: {statistics.mean(upload_stats['latencies']):.2f} ms")
        print(f"   p95 latency: {sorted(upload_stats['latencies'])[int(len(upload_stats['latencies'])*0.95)]:.2f} ms")
    
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="Upload DICOM files to MinIO cluster")
    parser.add_argument("--dir", default="./dicom_files", help="Directory containing DICOM files")
    parser.add_argument("--prefix", default="dicom", help="Key prefix in MinIO")
    args = parser.parse_args()
    
    upload_stats["total"] = len(list(Path(args.dir).glob("*.dcm")))
    upload_files_to_cluster(args.dir, prefix=args.prefix)

if __name__ == "__main__":
    main()
