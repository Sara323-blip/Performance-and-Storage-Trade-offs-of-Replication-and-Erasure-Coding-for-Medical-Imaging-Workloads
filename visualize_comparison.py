#!/usr/bin/env python3
"""
Create comparison charts for Replication-3 vs EC-4+2 vs EC-5+2
"""

import matplotlib.pyplot as plt
import numpy as np
import json
import os

# Load results
results_dir = "results"
with open(f"{results_dir}/comparison_results.json", 'r') as f:
    results = json.load(f)

# Extract data
configs = [r['config_name'] for r in results]
read_means = [r.get('read_mean', 0) for r in results]
read_p95s = [r.get('read_p95', 0) for r in results]
mixed_reads = [r.get('mixed_read_mean', 0) for r in results]
mixed_writes = [r.get('mixed_write_mean', 0) for r in results]
overheads = [r.get('storage_overhead_percent', 0) for r in results]

# Colors for different configuration types
colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

# Create figure with 2x2 subplots
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('DICOM Storage: Replication vs Erasure Coding Comparison', 
             fontsize=16, fontweight='bold')

# Plot 1: Read Latency (Mean vs p95)
ax1 = axes[0, 0]
x = np.arange(len(configs))
width = 0.35
bars1 = ax1.bar(x - width/2, read_means, width, label='Mean', color=colors[0])
bars2 = ax1.bar(x + width/2, read_p95s, width, label='p95', color=colors[1])
ax1.set_xlabel('Storage Configuration')
ax1.set_ylabel('Latency (ms)')
ax1.set_title('Read Performance (Lower is Better)')
ax1.set_xticks(x)
ax1.set_xticklabels(configs, rotation=15, ha='right')
ax1.legend()
ax1.grid(True, alpha=0.3)

# Add value labels
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{height:.0f}', ha='center', va='bottom', fontsize=9)

# Plot 2: Mixed Workload (Read vs Write)
ax2 = axes[0, 1]
bars3 = ax2.bar(x - width/2, mixed_reads, width, label='Read', color=colors[0])
bars4 = ax2.bar(x + width/2, mixed_writes, width, label='Write', color='#d62728')
ax2.set_xlabel('Storage Configuration')
ax2.set_ylabel('Latency (ms)')
ax2.set_title('Mixed Workload (70% Read / 30% Write)')
ax2.set_xticks(x)
ax2.set_xticklabels(configs, rotation=15, ha='right')
ax2.legend()
ax2.grid(True, alpha=0.3)

for bars in [bars3, bars4]:
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax2.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{height:.0f}', ha='center', va='bottom', fontsize=9)

# Plot 3: Storage Overhead
ax3 = axes[1, 0]
bars5 = ax3.bar(configs, overheads, color='#9467bd')
ax3.set_xlabel('Storage Configuration')
ax3.set_ylabel('Storage Overhead (%)')
ax3.set_title('Storage Efficiency (Lower is Better)')
ax3.set_xticklabels(configs, rotation=15, ha='right')
ax3.grid(True, alpha=0.3)

for bar in bars5:
    height = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2., height + 1,
            f'{height:.0f}%', ha='center', va='bottom', fontsize=10)

# Plot 4: Performance vs Overhead Trade-off
ax4 = axes[1, 1]
sizes = [max(r.get('mixed_write_mean', 20) * 5, 50) for r in results]
scatter = ax4.scatter(overheads, read_p95s, s=sizes, c=colors[:len(configs)], alpha=0.7, edgecolors='black')
ax4.set_xlabel('Storage Overhead (%)')
ax4.set_ylabel('Read p95 Latency (ms)')
ax4.set_title('Trade-off: Lower Overhead = Higher Latency')
ax4.grid(True, alpha=0.3)

for i, config in enumerate(configs):
    ax4.annotate(config, (overheads[i], read_p95s[i]), 
                xytext=(5, 5), textcoords='offset points', fontsize=9)

if len(overheads) > 2:
    z = np.polyfit(overheads, read_p95s, 1)
    p = np.poly1d(z)
    ax4.plot(overheads, p(overheads), "r--", alpha=0.5, 
             label=f'Trend: {z[0]:.1f} ms per 1% overhead')
    ax4.legend()

plt.tight_layout()
plt.savefig(f"{results_dir}/comparison_chart.png", dpi=150, bbox_inches='tight')
plt.show()

print(f"✅ Chart saved to {results_dir}/comparison_chart.png")