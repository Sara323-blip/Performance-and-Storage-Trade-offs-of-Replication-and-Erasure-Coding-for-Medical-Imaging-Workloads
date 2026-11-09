#!/usr/bin/env python3
"""
Upload DICOM files to MinIO cluster
"""

import boto3
import os
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Configuration
ENDPOINT = 'http://localhost:9101'
ACCESS_KEY = 'minioadmin'
SECRET_KEY = 'minioadmin123'
BUCKET_NAME = 'dicom-images'

def connect_minio():
    return boto3.client(
        's3',
        endpoint_url=ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        use_ssl=False
    )

def main():
    print("=" * 60)
    print("UPLOADING DICOM FILES TO MINIO")
    print("=" * 60)
    
    client = connect_minio()
    
    # Create bucket if it doesn't exist
    try:
        client.create_bucket(Bucket=BUCKET_NAME)
        print("✅ Created bucket: dicom-images")
    except:
        print("✅ Bucket already exists: dicom-images")
    
    # Find all DICOM files
    dicom_dir = Path("./dicom_files")
    dicom_files = list(dicom_dir.glob("*.dcm"))
    print(f"\n📁 Found {len(dicom_files)} DICOM files")
    
    if len(dicom_files) == 0:
        print("❌ No .dcm files found!")
        return
    
    # Upload files
    uploaded = 0
    failed = 0
    latencies = []
    
    print(f"\n📤 Uploading to MinIO...")
    print("-" * 40)
    
    for i, file_path in enumerate(dicom_files):
        key = f"dicom/image_{i:04d}.dcm"
        
        try:
            start = time.perf_counter()
            client.upload_file(str(file_path), BUCKET_NAME, key)
            elapsed_ms = (time.perf_counter() - start) * 1000
            uploaded += 1
            latencies.append(elapsed_ms)
            
            if (i + 1) % 20 == 0:
                print(f"   Uploaded {i+1}/{len(dicom_files)} files")
        except Exception as e:
            failed += 1
            print(f"   ❌ Failed: {file_path.name} - {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 UPLOAD SUMMARY")
    print("=" * 60)
    print(f"   Successful: {uploaded}")
    print(f"   Failed: {failed}")
    print(f"   Total data: {uploaded * 129 / 1024:.2f} MB")  # 129 KB per file
    
    if latencies:
        import statistics
        print(f"   Average latency: {statistics.mean(latencies):.2f} ms")
        print(f"   Min latency: {min(latencies):.2f} ms")
        print(f"   Max latency: {max(latencies):.2f} ms")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
