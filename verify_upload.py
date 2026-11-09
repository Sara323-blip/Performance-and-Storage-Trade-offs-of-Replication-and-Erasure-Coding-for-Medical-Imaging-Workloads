#!/usr/bin/env python3
"""
Verify uploaded files in MinIO
"""

import boto3

ENDPOINT = 'http://localhost:9101'
ACCESS_KEY = 'minioadmin'
SECRET_KEY = 'minioadmin123'
BUCKET_NAME = 'dicom-images'

client = boto3.client(
    's3',
    endpoint_url=ENDPOINT,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    use_ssl=False
)

print("=" * 60)
print("VERIFYING UPLOADED FILES")
print("=" * 60)

# List buckets
print("\n📦 Buckets:")
response = client.list_buckets()
buckets = [b['Name'] for b in response['Buckets']]
print(f"   {buckets}")

# List files in dicom-images bucket
print(f"\n📁 Files in '{BUCKET_NAME}':")
print("-" * 40)

try:
    response = client.list_objects_v2(Bucket=BUCKET_NAME, MaxKeys=50)
    
    if 'Contents' in response:
        total_size = 0
        for obj in response['Contents']:
            size_kb = obj['Size'] / 1024
            total_size += obj['Size']
            print(f"   {obj['Key']:<45} {size_kb:>8.1f} KB")
        
        print("-" * 40)
        print(f"   Total: {len(response['Contents'])} files")
        print(f"   Total size: {total_size / (1024*1024):.2f} MB")
    else:
        print("   No files found!")
        
except Exception as e:
    print(f"   Error: {e}")

print("=" * 60)
