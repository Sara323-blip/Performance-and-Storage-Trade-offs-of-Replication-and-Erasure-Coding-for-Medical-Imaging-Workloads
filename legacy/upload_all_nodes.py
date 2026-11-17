#!/usr/bin/env python3
"""
Upload DICOM files to all 5 MinIO nodes
"""

import boto3
import os
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# All 5 MinIO nodes
NODES = [
    ("node1", "http://localhost:9101"),
    ("node2", "http://localhost:9102"),
    ("node3", "http://localhost:9103"),
    ("node4", "http://localhost:9104"),
    ("node5", "http://localhost:9105"),
]

ACCESS_KEY = 'minioadmin'
SECRET_KEY = 'minioadmin123'
BUCKET_NAME = 'dicom-images'

def upload_to_node(node_name, endpoint, files):
    """Upload files to specific node"""
    client = boto3.client(
        's3', endpoint_url=endpoint,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        use_ssl=False
    )
    
    try:
        client.create_bucket(Bucket=BUCKET_NAME)
    except:
        pass
    
    for file_path in files:
        key = f"{node_name}/{file_path.name}"
        try:
            start = time.perf_counter()
            client.upload_file(str(file_path), BUCKET_NAME, key)
            latency = (time.perf_counter() - start) * 1000
            print(f"   [{node_name}] Uploaded {file_path.name} ({latency:.1f}ms)")
        except Exception as e:
            print(f"   ❌ [{node_name}] Failed: {e}")

def main():
    print("=" * 60)
    print("UPLOADING TO ALL 5 MINIO NODES")
    print("=" * 60)
    
    dicom_dir = Path("./dicom_files")
    dicom_files = list(dicom_dir.glob("*.dcm"))
    print(f"\n📁 Found {len(dicom_files)} DICOM files")
    
    if len(dicom_files) == 0:
        print("❌ No DICOM files found!")
        return
    
    # Split files across nodes
    files_per_node = len(dicom_files) // len(NODES)
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        for i, (node_name, endpoint) in enumerate(NODES):
            start = i * files_per_node
            end = start + files_per_node if i < len(NODES)-1 else len(dicom_files)
            node_files = dicom_files[start:end]
            executor.submit(upload_to_node, node_name, endpoint, node_files)
    
    print("\n✅ Upload complete!")

if __name__ == "__main__":
    main()
