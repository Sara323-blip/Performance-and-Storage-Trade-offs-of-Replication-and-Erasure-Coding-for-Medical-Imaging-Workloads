#!/usr/bin/env python3
"""
Generate LaTeX table for thesis with 3 configurations
"""

import json

with open("results/comparison_results.json", 'r') as f:
    results = json.load(f)

# Generate LaTeX table
latex_table = r"""
\begin{table}[htbp]
\centering
\caption{Performance Comparison: Replication vs. Erasure Coding for DICOM Storage}
\label{tab:storage_comparison}
\begin{tabular}{lcccccc}
\toprule
\textbf{Configuration} & \textbf{Type} & \textbf{Storage Overhead} & \textbf{Read Mean} & \textbf{Read p95} & \textbf{Mixed Read} & \textbf{Mixed Write} \\
\midrule
"""

for r in results:
    latex_table += f"{r['config_name']} & {r['config_type']} & {r['storage_overhead_percent']}\% & {r.get('read_mean', 'N/A'):.1f} ms & {r.get('read_p95', 'N/A'):.1f} ms & {r.get('mixed_read_mean', 'N/A'):.1f} ms & {r.get('mixed_write_mean', 'N/A'):.1f} ms \\\\\n"

latex_table += r"""
\bottomrule
\end{tabular}
\end{table}
"""

# Save LaTeX table
with open("results/comparison_table.tex", 'w') as f:
    f.write(latex_table)

print("✅ LaTeX table saved to results/comparison_table.tex")
print("\n" + latex_table)

# Generate clinical recommendations
print("\n" + "=" * 70)
print("🏥 CLINICAL RECOMMENDATIONS")
print("=" * 70)

for r in results:
    if r['config_name'] == 'Replication-3':
        print(f"\n📊 {r['config_name']} ({r['config_type']}):")
        print(f"   → Best for: Active clinical care, emergency departments")
        print(f"   → Read p95: {r.get('read_p95', 'N/A')} ms")
        print(f"   → Trade-off: {r['storage_overhead_percent']}% storage overhead")
    
    elif r['config_name'] == 'EC-4+2':
        print(f"\n📊 {r['config_name']} ({r['config_type']}):")
        print(f"   → Best for: Balanced hospital workloads")
        print(f"   → Read p95: {r.get('read_p95', 'N/A')} ms")
        print(f"   → Trade-off: {r['storage_overhead_percent']}% storage overhead")
    
    elif r['config_name'] == 'EC-5+2':
        print(f"\n📊 {r['config_name']} ({r['config_type']}):")
        print(f"   → Best for: Cost-sensitive storage with good performance")
        print(f"   → Read p95: {r.get('read_p95', 'N/A')} ms")
        print(f"   → Trade-off: {r['storage_overhead_percent']}% storage overhead")

print("\n" + "=" * 70)