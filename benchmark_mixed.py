#!/usr/bin/env python3
"""
Mixed workload benchmark (reads + writes) for DICOM storage
Simulates clinical workload: 70% reads, 30% writes
"""

import boto3
import time
import statistics
import random
from concurrent.futures import ThreadPoolExecutor
import json

# MinIO node
ENDPOINT = 'http://localhost:9101'  # Use node1 as primary
ACCESS_KEY = 'minioadmin'
SECRET_KEY = 'minioadmin123'
BUCKET_NAME = 'dicom-images'

# Workload configuration
READ_PERCENT = 70  # 70% reads, 30% writes
TEST_DURATION_SEC = 60  # Run for 60 seconds
FILE_SIZE_KB = 100  # 100KB test files

def generate_test_data(size_kb):
    """Generate random test data"""
    return b'X' * (size_kb * 1024)

def run_workload(duration_sec, read_pct=70):
    """Run mixed read/write workload"""
    
    client = boto3.client(
        's3',
        endpoint_url=ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        use_ssl=False
    )
    
    # Ensure bucket exists
    try:
        client.create_bucket(Bucket=BUCKET_NAME)
    except:
        pass
    
    results = {
        "reads": [],
        "writes": [],
        "operations": 0,
        "start_time": time.time()
    }
    
    write_counter = 0
    
    print(f"\n🏃 Running workload for {duration_sec} seconds...")
    print(f"   Read %: {read_pct}% | Write %: {100-read_pct}%")
    print("-" * 50)
    
    start_time = time.time()
    
    while time.time() - start_time < duration_sec:
        # Decide operation type based on percentages
        if random.randint(1, 100) <= read_pct:
            # READ operation - try to read existing files
            try:
                response = client.list_objects_v2(Bucket=BUCKET_NAME, MaxKeys=10)
                if 'Contents' in response and response['Contents']:
                    key = random.choice(response['Contents'])['Key']
                    read_start = time.perf_counter()
                    obj = client.get_object(Bucket=BUCKET_NAME, Key=key)
                    obj['Body'].read()
                    latency = (time.perf_counter() - read_start) * 1000
                    results["reads"].append(latency)
                else:
                    # No files yet, do a write instead
                    continue
            except Exception as e:
                pass
        else:
            # WRITE operation
            write_key = f"benchmark/write_{write_counter}_{time.time()}.dat"
            data = generate_test_data(FILE_SIZE_KB)
            write_start = time.perf_counter()
            client.put_object(Bucket=BUCKET_NAME, Key=write_key, Body=data)
            latency = (time.perf_counter() - write_start) * 1000
            results["writes"].append(latency)
            write_counter += 1
        
        results["operations"] += 1
    
    return results

def main():
    print("=" * 70)
    print("MIXED WORKLOAD BENCHMARK (Clinical Simulation)")
    print("=" * 70)
    
    # Run benchmark
    results = run_workload(TEST_DURATION_SEC, READ_PERCENT)
    
    # Calculate statistics
    print("\n" + "=" * 70)
    print("📊 BENCHMARK RESULTS")
    print("=" * 70)
    print(f"\n⏱️  Duration: {TEST_DURATION_SEC} seconds")
    print(f"📈 Total operations: {results['operations']}")
    
    if results['reads']:
        print(f"\n📖 READ OPERATIONS: {len(results['reads'])}")
        print(f"   Mean latency: {statistics.mean(results['reads']):.2f} ms")
        print(f"   p50: {statistics.median(results['reads']):.2f} ms")
        print(f"   p95: {statistics.quantiles(results['reads'], n=100)[94]:.2f} ms")
        print(f"   p99: {statistics.quantiles(results['reads'], n=100)[98]:.2f} ms")
    
    if results['writes']:
        print(f"\n✍️  WRITE OPERATIONS: {len(results['writes'])}")
        print(f"   Mean latency: {statistics.mean(results['writes']):.2f} ms")
        print(f"   p50: {statistics.median(results['writes']):.2f} ms")
        print(f"   p95: {statistics.quantiles(results['writes'], n=100)[94]:.2f} ms")
        print(f"   p99: {statistics.quantiles(results['writes'], n=100)[98]:.2f} ms")
    
    # Clean up test files
    print("\n🧹 Cleaning up test files...")
    client = boto3.client('s3', endpoint_url=ENDPOINT,
                          aws_access_key_id=ACCESS_KEY,
                          aws_secret_access_key=SECRET_KEY,
                          use_ssl=False)
    
    try:
        response = client.list_objects_v2(Bucket=BUCKET_NAME, Prefix="benchmark/")
        if 'Contents' in response:
            for obj in response['Contents']:
                client.delete_object(Bucket=BUCKET_NAME, Key=obj['Key'])
            print(f"   Deleted {len(response['Contents'])} test files")
    except:
        pass
    
    print("\n✅ Benchmark complete!")

if __name__ == "__main__":
    main()
