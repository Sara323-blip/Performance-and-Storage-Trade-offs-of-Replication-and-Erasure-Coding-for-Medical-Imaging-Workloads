#!/usr/bin/env python3
"""
Collect all benchmark results into a single CSV file
"""

import csv
import re
import os

results_dir = "results"
os.makedirs(results_dir, exist_ok=True)

# Define configurations
configs = ["replication3", "ec42", "ec82"]
metrics = ["read_mean", "read_p95", "write_mean", "write_p95"]

# Parse results from text files
all_data = []

for config in configs:
    read_file = f"{results_dir}/{config}_read.txt"
    mixed_file = f"{results_dir}/{config}_mixed.txt"
    
    data = {"config": config.upper()}
    
    # Parse read benchmark
    if os.path.exists(read_file):
        with open(read_file, 'r') as f:
            content = f.read()
            # Extract mean and p95
            mean_match = re.search(r'Mean: ([\d.]+) ms', content)
            p95_match = re.search(r'p95: ([\d.]+) ms', content)
            if mean_match:
                data["read_mean"] = float(mean_match.group(1))
            if p95_match:
                data["read_p95"] = float(p95_match.group(1))
    
    # Parse mixed benchmark
    if os.path.exists(mixed_file):
        with open(mixed_file, 'r') as f:
            content = f.read()
            read_mean_match = re.search(r'READ OPERATIONS.*?Mean latency: ([\d.]+) ms', content, re.DOTALL)
            read_p95_match = re.search(r'READ OPERATIONS.*?p95: ([\d.]+) ms', content, re.DOTALL)
            write_mean_match = re.search(r'WRITE OPERATIONS.*?Mean latency: ([\d.]+) ms', content, re.DOTALL)
            write_p95_match = re.search(r'WRITE OPERATIONS.*?p95: ([\d.]+) ms', content, re.DOTALL)
            
            if read_mean_match:
                data["mixed_read_mean"] = float(read_mean_match.group(1))
            if read_p95_match:
                data["mixed_read_p95"] = float(read_p95_match.group(1))
            if write_mean_match:
                data["mixed_write_mean"] = float(write_mean_match.group(1))
            if write_p95_match:
                data["mixed_write_p95"] = float(write_p95_match.group(1))
    
    all_data.append(data)

# Write to CSV
csv_file = f"{results_dir}/comparison_results.csv"
with open(csv_file, 'w', newline='') as f:
    fieldnames = ["config", "read_mean", "read_p95", "mixed_read_mean", "mixed_read_p95", "mixed_write_mean", "mixed_write_p95"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for data in all_data:
        writer.writerow(data)

print(f"✅ Results saved to {csv_file}")
print("\n📊 Summary:")
print("-" * 60)
for data in all_data:
    print(f"\n{data['config']}:")
    print(f"   Read: {data.get('read_mean', 'N/A')} ms (mean), {data.get('read_p95', 'N/A')} ms (p95)")
    print(f"   Mixed Read: {data.get('mixed_read_mean', 'N/A')} ms")
    print(f"   Mixed Write: {data.get('mixed_write_mean', 'N/A')} ms")
