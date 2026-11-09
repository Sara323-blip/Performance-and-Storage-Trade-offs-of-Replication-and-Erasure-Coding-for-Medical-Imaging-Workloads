#!/usr/bin/env python3
"""
Visualize benchmark results
"""

import json
import matplotlib.pyplot as plt
import numpy as np

# Load results if saved
try:
    with open("benchmark_results.json", "r") as f:
        results = json.load(f)
except:
    print("No benchmark_results.json found. Run benchmark_read.py first.")
    exit(1)

# Extract data
nodes = []
mean_latencies = []
p95_latencies = []

for result in results:
    if result.get('error') is None and result.get('latencies'):
        nodes.append(result['node'])
        latencies = result['latencies']
        mean_latencies.append(np.mean(latencies))
        p95_latencies.append(np.percentile(latencies, 95))

if not nodes:
    print("No valid data to plot")
    exit(1)

# Create bar chart
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# Mean latency bars
colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
bars1 = ax1.bar(nodes, mean_latencies, color=colors[:len(nodes)])
ax1.set_xlabel('MinIO Node')
ax1.set_ylabel('Mean Read Latency (ms)')
ax1.set_title('Mean Read Latency by Node')
ax1.grid(True, alpha=0.3)

# Add value labels on bars
for bar, val in zip(bars1, mean_latencies):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
             f'{val:.1f}ms', ha='center', va='bottom', fontsize=10)

# p95 latency bars
bars2 = ax2.bar(nodes, p95_latencies, color=colors[:len(nodes)])
ax2.set_xlabel('MinIO Node')
ax2.set_ylabel('p95 Read Latency (ms)')
ax2.set_title('p95 Read Latency by Node')
ax2.grid(True, alpha=0.3)

for bar, val in zip(bars2, p95_latencies):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
             f'{val:.1f}ms', ha='center', va='bottom', fontsize=10)

plt.tight_layout()
plt.savefig('benchmark_chart.png', dpi=150)
plt.show()

print("\n✅ Chart saved to benchmark_chart.png")
