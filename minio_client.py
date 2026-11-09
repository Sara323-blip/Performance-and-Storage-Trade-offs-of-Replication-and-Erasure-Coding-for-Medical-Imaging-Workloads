#!/usr/bin/env python3
"""
MinIO Python client to replace mc commands
"""

import boto3
import json
from datetime import datetime

ENDPOINT = 'http://localhost:9101'
ACCESS_KEY = 'minioadmin'
SECRET_KEY = 'minioadmin123'
BUCKET_NAME = 'dicom-images'

def get_client():
    return boto3.client(
        's3',
        endpoint_url=ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        use_ssl=False
    )

def list_files():
    """List all files in bucket"""
    client = get_client()
    try:
        response = client.list_objects_v2(Bucket=BUCKET_NAME, MaxKeys=50)
        if 'Contents' in response:
            print(f"\n📁 Objects in {BUCKET_NAME}:")
            print("-" * 50)
            for obj in response['Contents']:
                size_kb = obj['Size'] / 1024
                print(f"   {obj['Key']:<50} {size_kb:>8.1f} KB")
            print(f"\n   Total: {len(response['Contents'])} objects")
        else:
            print(f"\n❌ No objects found in {BUCKET_NAME}")
    except Exception as e:
        print(f"Error: {e}")

def bucket_info():
    """Get bucket information"""
    client = get_client()
    try:
        response = client.list_buckets()
        buckets = [b['Name'] for b in response['Buckets']]
        print(f"\n📦 Buckets: {buckets}")
        print(f"   Total buckets: {len(buckets)}")
    except Exception as e:
        print(f"Error: {e}")

def upload_file(local_path, remote_key):
    """Upload a single file"""
    client = get_client()
    try:
        client.upload_file(local_path, BUCKET_NAME, remote_key)
        print(f"✅ Uploaded: {remote_key}")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def main():
    print("=" * 50)
    print("MINIO PYTHON CLIENT")
    print("=" * 50)
    
    bucket_info()
    list_files()

if __name__ == "__main__":
    main()
