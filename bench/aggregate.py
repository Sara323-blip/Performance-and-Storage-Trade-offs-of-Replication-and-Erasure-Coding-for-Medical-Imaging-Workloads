"""Turn the raw CSV files of a run into the paper's table and numbers.

  python -m bench.aggregate results/<run_id>

Writes into the run directory:
  summary.csv   one row per configuration: mean and 95% confidence half-width across repetitions
  table_x.tex   LaTeX table (replaces the hand-typed Table X)
  numbers.tex   \\newcommand macros for every number quoted in the text, so text and table cannot disagree
Everything is computed from the raw per-operation CSV files with nearest-rank percentiles.
"""
import csv
import json
import os
import re
import sys

from .common import load_settings, mean_ci, summarize

METRICS = ["read_mean", "read_p50", "read_p95", "read_p99", "mixed_read_mean", "mixed_read_p95",
           "mixed_write_mean", "mixed_write_p95", "mixed_ops", "overhead_pct", "read_fail", "mixed_fail"]


def read_rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def one_rep(rep_dir):
    m = {}
    rr = read_rows(os.path.join(rep_dir, "read.csv"))
    s = summarize([float(r["ms"]) for r in rr if r["ok"] == "True"])
    m.update(read_mean=s["mean"], read_p50=s["p50"], read_p95=s["p95"], read_p99=s["p99"],
             read_fail=sum(1 for r in rr if r["ok"] != "True"))
    mr = read_rows(os.path.join(rep_dir, "mixed.csv"))
    for op in ("read", "write"):
        s = summarize([float(r["ms"]) for r in mr if r["op"] == op and r["ok"] == "True"])
        m[f"mixed_{op}_mean"], m[f"mixed_{op}_p95"] = s["mean"], s["p95"]
    m["mixed_ops"] = len(mr)
    m["mixed_fail"] = sum(1 for r in mr if r["ok"] != "True")
    with open(os.path.join(rep_dir, "overhead.json")) as f:
        m["overhead_pct"] = json.load(f)["overhead_pct"]
    return m


def aggregate(run_dir):
    out = {}
    for cfg in sorted(os.listdir(run_dir)):
        cdir = os.path.join(run_dir, cfg)
        if not os.path.isdir(cdir):
            continue
        reps = [one_rep(os.path.join(cdir, r)) for r in sorted(os.listdir(cdir))
                if r.startswith("rep") and os.path.exists(os.path.join(cdir, r, "mixed.csv"))]
        if not reps:
            continue
        out[cfg] = {"n_reps": len(reps)}
        for k in METRICS:
            out[cfg][k] = mean_ci([r[k] for r in reps])
    return out


def fmt(mc, nd=1):
    m, ci = mc
    return f"{m:.{nd}f}" if ci != ci else f"{m:.{nd}f} $\\pm$ {ci:.{nd}f}"


_DIGITS = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
_SUFFIX = {"read_mean": "ReadMean", "read_p95": "ReadPNinetyFive", "mixed_read_mean": "MixedReadMean",
           "mixed_write_mean": "MixedWriteMean", "overhead_pct": "OverheadPct"}


def macro_name(cfg):
    """LaTeX macro names may only contain letters: ec-4+2 -> EcFourPTwo."""
    out = ""
    for ch in cfg:
        if ch.isdigit():
            out += _DIGITS[int(ch)]
        elif ch == "+":
            out += "P"
        elif ch.isalpha():
            out += ch.upper() if not out else ch
    return out


def write_outputs(run_dir, agg, labels, baseline):
    with open(os.path.join(run_dir, "summary.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["config", "reps"] + [x for k in METRICS for x in (k, k + "_ci95")])
        for cfg, v in agg.items():
            w.writerow([cfg, v["n_reps"]] + [x for k in METRICS for x in v[k]])

    lines = [r"\begin{tabular}{@{}lrrrrrrrr@{}}", r"\toprule",
             r"Configuration & Overhead (\%) & Read mean & Read p95 & Mixed read & Mixed write & Mixed ops & Reps \\",
             r"\midrule"]
    for cfg, v in agg.items():
        lines.append(f"{labels.get(cfg, cfg)} & {fmt(v['overhead_pct'], 0)} & {fmt(v['read_mean'])} & "
                     f"{fmt(v['read_p95'])} & {fmt(v['mixed_read_mean'])} & {fmt(v['mixed_write_mean'])} & "
                     f"{v['mixed_ops'][0]:.0f} & {v['n_reps']} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    with open(os.path.join(run_dir, "table_x.tex"), "w") as f:
        f.write("\n".join(lines) + "\n")

    macros = []
    base = agg.get(baseline)
    for cfg, v in agg.items():
        n = macro_name(cfg)
        for k, suffix in _SUFFIX.items():
            macros.append(f"\\newcommand{{\\{n}{suffix}}}{{{v[k][0]:.1f}}}")
        if base and cfg != baseline:
            for k in ("read_mean", "read_p95", "mixed_write_mean"):
                rel = (v[k][0] / base[k][0] - 1) * 100
                macros.append(f"\\newcommand{{\\{n}{_SUFFIX[k]}VsBasePct}}{{{rel:+.0f}}}")
    with open(os.path.join(run_dir, "numbers.tex"), "w") as f:
        f.write("\n".join(macros) + "\n")


def main():
    run_dir = sys.argv[1]
    settings = load_settings()
    labels = {k: v["label"] for k, v in settings["configs"].items()}
    agg = aggregate(run_dir)
    if not agg:
        sys.exit("no complete repetitions found")
    write_outputs(run_dir, agg, labels, baseline="repl-3")
    print(f"wrote summary.csv, table_x.tex, numbers.tex in {run_dir}")


if __name__ == "__main__":
    main()
