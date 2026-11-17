"""Verify the real erasure layout and measure real on-disk storage overhead.

layout:   asks the running cluster (mc admin info --json) how many drives per erasure set and which
          parity it uses, and compares with what the configuration claims. A mismatch aborts the run.
overhead: sums the apparent size of every file under the data directory before and after the upload
          (the same number as `du -sb`), so MinIO's own metadata and per-object xl.meta are included.
"""
import json
import os
import subprocess


def _walk_find(obj, key):
    """First value for `key` anywhere in a nested JSON structure."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = _walk_find(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _walk_find(v, key)
            if r is not None:
                return r
    return None


def mc_info(endpoint, user, password):
    host = endpoint.replace("http://", "")
    env = dict(os.environ, MC_HOST_bench=f"http://{user}:{password}@{host}")
    out = subprocess.run(["mc", "admin", "info", "--json", "bench"], capture_output=True, text=True, env=env, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(f"mc admin info failed: {out.stderr.strip() or out.stdout.strip()}")
    text = out.stdout.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(text.splitlines()[-1])


def read_layout(info):
    def first(v):
        return v[0] if isinstance(v, list) and v else v
    return {
        "backend_type": _walk_find(info, "backendType"),
        "online_drives": _walk_find(info, "onlineDisks"),
        "offline_drives": _walk_find(info, "offlineDisks"),
        "standard_parity": _walk_find(info, "standardSCParity"),
        "sets": first(_walk_find(info, "totalSets")),
        "drives_per_set": first(_walk_find(info, "totalDrivesPerSet")),
    }


def check_layout(cfg, layout):
    """Return a list of problems (empty when the cluster matches the configuration)."""
    problems = []
    if cfg["type"] != "ec":
        return problems
    if layout["drives_per_set"] != cfg["drives"]:
        problems.append(f"drives per set is {layout['drives_per_set']}, configuration says {cfg['drives']}")
    if layout["sets"] != 1:
        problems.append(f"{layout['sets']} erasure sets, expected 1")
    if layout["standard_parity"] != cfg["m"]:
        problems.append(f"standard parity is {layout['standard_parity']}, configuration says {cfg['m']}")
    return problems


def dir_bytes(path):
    """Apparent size of all regular files under `path` (like du -sb)."""
    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.lstat(os.path.join(root, f)).st_size
            except OSError:
                pass
    return total


def overhead(before_bytes, after_bytes, raw_bytes):
    """Measured storage overhead in percent: (bytes the upload added on disk / raw bytes uploaded) - 1.

    For client-side 3x replication all three copies are on disk, so this is about 200 %.
    """
    return ((after_bytes - before_bytes) / raw_bytes - 1.0) * 100.0 if raw_bytes else float("nan")
