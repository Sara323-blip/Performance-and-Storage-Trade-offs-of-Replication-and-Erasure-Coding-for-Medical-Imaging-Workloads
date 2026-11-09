#!/usr/bin/env python3
"""
Test connectivity to all 5 MinIO nodes
"""

import boto3
import time

NODES = {
    "Node 1 (9101)": "http://localhost:9101",
    "Node 2 (9102)": "http://localhost:9102",
    "Node 3 (9103)": "http://localhost:9103",
    "Node 4 (9104)": "http://localhost:9104",
    "Node 5 (9105)": "http://localhost:9105",
}

ACCESS_KEY = 'minioadmin'
SECRET_KEY = 'minioadmin123'
BUCKET_NAME = 'dicom-images'

print("=" * 60)
print("TESTING ALL 5 MINIO NODES")
print("=" * 60)

for node_name, endpoint in NODES.items():
    try:
        client = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY,
            use_ssl=False
        )
        
        start = time.perf_counter()
        response = client.list_buckets()
        latency = (time.perf_counter() - start) * 1000
        
        # Count objects in dicom-images
        try:
            obj_response = client.list_objects_v2(Bucket=BUCKET_NAME, MaxKeys=1000)
            obj_count = len(obj_response.get('Contents', []))
        except:
            obj_count = 0
        
        print(f"\n✅ {node_name}")
        print(f"   Connection latency: {latency:.2f} ms")
        print(f"   Objects visible: {obj_count}")
        
    except Exception as e:
        print(f"\n❌ {node_name}: {e}")

print("\n" + "=" * 60)
