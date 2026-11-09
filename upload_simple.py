#!/usr/bin/env python3
"""
Simplified upload to single MinIO node first (easier to debug)
"""

import boto3
import os
import time
from pathlib import Path

# MinIO connection (use Node 1)
ENDPOINT = 'http://localhost:9101'
ACCESS_KEY = 'minioadmin'
SECRET_KEY = 'minioadmin123'
BUCKET_NAME = 'dicom-images'

print("=" * 60)
print("UPLOADING DICOM FILES TO MINIO")
print("=" * 60)

# Connect
client = boto3.client(
    's3',
    endpoint_url=ENDPOINT,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    use_ssl=False
)

# Create bucket
try:
    client.create_bucket(Bucket=BUCKET_NAME)
    print(f"✅ Created bucket: {BUCKET_NAME}")
except:
    print(f"✅ Bucket already exists: {BUCKET_NAME}")

# Find DICOM files
dicom_dir = Path("./dicom_files")
dicom_files = list(dicom_dir.glob("*.dcm"))
print(f"\n📁 Found {len(dicom_files)} DICOM files")

if len(dicom_files) == 0:
    print("❌ No DICOM files found! Run minimal_dicom.py first.")
    exit(1)

# Upload files
print(f"\n📤 Uploading files to MinIO...")
print("-" * 40)

success = 0
failed = 0
latencies = []

for i, file_path in enumerate(dicom_files):
    key = f"upload_{i:04d}.dcm"
    file_size = file_path.stat().st_size
    
    try:
        start = time.perf_counter()
        client.upload_file(str(file_path), BUCKET_NAME, key)
        latency = (time.perf_counter() - start) * 1000
        success += 1
        latencies.append(latency)
        
        if (i + 1) % 20 == 0:
            print(f"   Uploaded {i+1}/{len(dicom_files)} files")
    except Exception as e:
        failed += 1
        print(f"   ❌ Failed: {file_path.name} - {e}")

print("\n" + "=" * 60)
print("📊 UPLOAD SUMMARY")
print("=" * 60)
print(f"   Successful: {success}")
print(f"   Failed: {failed}")

if latencies:
    import statistics
    print(f"   Average latency: {statistics.mean(latencies):.2f} ms")
    print(f"   Min latency: {min(latencies):.2f} ms")
    print(f"   Max latency: {max(latencies):.2f} ms")

print("=" * 60)
