#!/usr/bin/env python3
"""
Collect and compare results from all storage configurations
"""

import re
import os
import json
from pathlib import Path

# Results directory
results_dir = "results"
os.makedirs(results_dir, exist_ok=True)

# Define configurations to analyze (UPDATED with EC-5+2)
configs = [
    {"name": "Replication-3", "file_prefix": "replication3", "overhead": 200, "type": "Replication"},
    {"name": "EC-4+2", "file_prefix": "ec42", "overhead": 50, "type": "Erasure Coding"},
    {"name": "EC-5+2", "file_prefix": "ec52", "overhead": 40, "type": "Erasure Coding"},
]

def parse_read_results(filepath):
    """Parse read benchmark results"""
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    results = {}
    
    # Extract metrics
    mean_match = re.search(r'Mean: ([\d.]+) ms', content)
    p95_match = re.search(r'p95: ([\d.]+) ms', content)
    p99_match = re.search(r'p99: ([\d.]+) ms', content)
    min_match = re.search(r'Min: ([\d.]+) ms', content)
    max_match = re.search(r'Max: ([\d.]+) ms', content)
    
    if mean_match:
        results['read_mean'] = float(mean_match.group(1))
    if p95_match:
        results['read_p95'] = float(p95_match.group(1))
    if p99_match:
        results['read_p99'] = float(p99_match.group(1))
    if min_match:
        results['read_min'] = float(min_match.group(1))
    if max_match:
        results['read_max'] = float(max_match.group(1))
    
    return results

def parse_mixed_results(filepath):
    """Parse mixed workload benchmark results"""
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    results = {}
    
    # Extract read metrics
    read_mean_match = re.search(r'READ OPERATIONS: \d+\n   Mean latency: ([\d.]+) ms', content)
    read_p95_match = re.search(r'READ OPERATIONS:.*?p95: ([\d.]+) ms', content, re.DOTALL)
    
    # Extract write metrics
    write_mean_match = re.search(r'WRITE OPERATIONS: \d+\n   Mean latency: ([\d.]+) ms', content)
    write_p95_match = re.search(r'WRITE OPERATIONS:.*?p95: ([\d.]+) ms', content, re.DOTALL)
    
    if read_mean_match:
        results['mixed_read_mean'] = float(read_mean_match.group(1))
    if read_p95_match:
        results['mixed_read_p95'] = float(read_p95_match.group(1))
    if write_mean_match:
        results['mixed_write_mean'] = float(write_mean_match.group(1))
    if write_p95_match:
        results['mixed_write_p95'] = float(write_p95_match.group(1))
    
    return results

def main():
    print("=" * 70)
    print("📊 COLLECTING BENCHMARK RESULTS")
    print("=" * 70)
    
    all_results = []
    
    for config in configs:
        print(f"\n📁 Processing {config['name']}...")
        
        read_file = f"{results_dir}/{config['file_prefix']}_read.txt"
        mixed_file = f"{results_dir}/{config['file_prefix']}_mixed.txt"
        
        read_data = parse_read_results(read_file)
        mixed_data = parse_mixed_results(mixed_file)
        
        result = {
            "config_name": config['name'],
            "config_type": config['type'],
            "storage_overhead_percent": config['overhead'],
        }
        
        if read_data:
            result.update(read_data)
            print(f"   ✅ Read benchmark: {read_data.get('read_mean', 'N/A')} ms (mean), {read_data.get('read_p95', 'N/A')} ms (p95)")
        else:
            print(f"   ⚠️ Read benchmark file not found")
        
        if mixed_data:
            result.update(mixed_data)
            print(f"   ✅ Mixed benchmark: Read {mixed_data.get('mixed_read_mean', 'N/A')} ms, Write {mixed_data.get('mixed_write_mean', 'N/A')} ms")
        else:
            print(f"   ⚠️ Mixed benchmark file not found")
        
        all_results.append(result)
    
    # Save to JSON
    with open(f"{results_dir}/comparison_results.json", 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print("\n" + "=" * 70)
    print("📊 COMPARISON SUMMARY TABLE")
    print("=" * 70)
    print(f"{'Configuration':15} | {'Type':13} | {'Overhead':9} | {'Read Mean':10} | {'Read p95':10} | {'Mixed Read':10} | {'Mixed Write':11}")
    print("-" * 85)
    
    for r in all_results:
        print(f"{r['config_name']:15} | {r['config_type']:13} | {r.get('storage_overhead_percent', 0):>3}%      | {r.get('read_mean', 0):>8.1f} ms | {r.get('read_p95', 0):>8.1f} ms | {r.get('mixed_read_mean', 0):>8.1f} ms | {r.get('mixed_write_mean', 0):>9.1f} ms")
    
    print("=" * 70)
    
    # Save as CSV for Excel
    import csv
    csv_file = f"{results_dir}/comparison_results.csv"
    with open(csv_file, 'w', newline='') as f:
        if all_results:
            fieldnames = ['config_name', 'config_type', 'storage_overhead_percent', 
                         'read_mean', 'read_p95', 'read_p99',
                         'mixed_read_mean', 'mixed_read_p95', 
                         'mixed_write_mean', 'mixed_write_p95']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in all_results:
                writer.writerow(r)
    
    print(f"\n✅ Results saved to:")
    print(f"   JSON: {results_dir}/comparison_results.json")
    print(f"   CSV:  {results_dir}/comparison_results.csv")
    
    return all_results

if __name__ == "__main__":
    results = main()