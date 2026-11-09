#!/usr/bin/env python3
"""
Benchmark read performance across all 5 MinIO nodes
"""

import boto3
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
import json

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

def test_node_read_performance(node_name, endpoint, num_reads=50):
    """Test read performance on a specific node"""
    
    client = boto3.client(
        's3',
        endpoint_url=endpoint,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        use_ssl=False
    )
    
    # List objects in bucket (from this node's perspective)
    try:
        response = client.list_objects_v2(Bucket=BUCKET_NAME, MaxKeys=num_reads)
        if 'Contents' not in response:
            return {"node": node_name, "error": "No objects found", "latencies": []}
        
        objects = response['Contents']
        print(f"   [{node_name}] Found {len(objects)} objects")
        
    except Exception as e:
        return {"node": node_name, "error": str(e), "latencies": []}
    
    # Measure read latency for each object
    latencies = []
    successful_reads = 0
    
    for obj in objects:
        key = obj['Key']
        try:
            start = time.perf_counter()
            response = client.get_object(Bucket=BUCKET_NAME, Key=key)
            response['Body'].read()
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)
            successful_reads += 1
        except Exception as e:
            print(f"   [{node_name}] Failed to read {key}: {e}")
    
    return {
        "node": node_name,
        "successful_reads": successful_reads,
        "latencies": latencies,
        "error": None
    }

def main():
    print("=" * 70)
    print("MINIO CLUSTER READ PERFORMANCE BENCHMARK")
    print("=" * 70)
    print("\n📊 Testing read performance across 5 nodes...\n")
    
    # Run tests on all nodes in parallel
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(test_node_read_performance, name, url, 50) 
                   for name, url in NODES]
        
        for future in futures:
            result = future.result()
            results.append(result)
    
    # Display results
    print("\n" + "=" * 70)
    print("📊 READ LATENCY RESULTS (milliseconds)")
    print("=" * 70)
    
    all_latencies = []
    
    for result in results:
        print(f"\n🔹 {result['node']}:")
        if result['error']:
            print(f"   ❌ Error: {result['error']}")
            continue
        
        latencies = result['latencies']
        if not latencies:
            print("   ⚠️ No successful reads")
            continue
        
        all_latencies.extend(latencies)
        
        print(f"   Successful reads: {result['successful_reads']}")
        print(f"   Mean: {statistics.mean(latencies):.2f} ms")
        print(f"   Median: {statistics.median(latencies):.2f} ms")
        print(f"   p95: {statistics.quantiles(latencies, n=100)[94]:.2f} ms")
        print(f"   p99: {statistics.quantiles(latencies, n=100)[98]:.2f} ms")
        print(f"   Min: {min(latencies):.2f} ms")
        print(f"   Max: {max(latencies):.2f} ms")
    
    # Overall cluster performance
    if all_latencies:
        print("\n" + "=" * 70)
        print("📊 OVERALL CLUSTER PERFORMANCE")
        print("=" * 70)
        print(f"   Total reads: {len(all_latencies)}")
        print(f"   Cluster Mean: {statistics.mean(all_latencies):.2f} ms")
        print(f"   Cluster p95: {statistics.quantiles(all_latencies, n=100)[94]:.2f} ms")
        print(f"   Cluster p99: {statistics.quantiles(all_latencies, n=100)[98]:.2f} ms")
    
    # Save results
    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\n✅ Results saved to benchmark_results.json")

if __name__ == "__main__":
    main()
