"""Upload, read-only and mixed workloads. Every operation is returned as a row; nothing is parsed from text."""
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor

from .common import dataset_files, summarize

PREFIX = "dicom/"


def upload_dataset(store, directory):
    """Upload every dataset file once (client-side 3x for replication). Returns rows (key, ms, ok)."""
    rows = []
    store.ensure_bucket()
    for name in dataset_files(directory):
        with open(os.path.join(directory, name), "rb") as f:
            data = f.read()
        ms, _, ok = store.put(PREFIX + name, data)
        rows.append((PREFIX + name, ms, ok))
    return rows


def raw_bytes(directory):
    return sum(os.path.getsize(os.path.join(directory, n)) for n in dataset_files(directory))


def read_workload(store, directory, reads, warmup, seed, concurrency=1):
    """Random reads over ALL uploaded objects. The first `warmup` reads are discarded.

    Returns rows (op_index, key, endpoint, latency_ms, ok) for the timed reads.
    """
    keys = [PREFIX + n for n in dataset_files(directory)]
    rng = random.Random(seed)
    plan = [rng.choice(keys) for _ in range(warmup + reads)]

    def one(i):
        ms, ep, ok = store.get(plan[i])
        return i, plan[i], ep, ms, ok

    if concurrency <= 1:
        results = [one(i) for i in range(len(plan))]
    else:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            results = list(pool.map(one, range(len(plan))))
    return [r for r in results if r[0] >= warmup]


def mixed_workload(store, directory, duration_sec, warmup_sec, read_pct, seed):
    """Time-bounded 70/30 workload.

    Reads pick a random uploaded dataset object (not a fixed handful); writes store a random payload of
    the same size as the dataset objects, so writes are neither compressible nor smaller than reads.
    The first `warmup_sec` seconds are discarded. Returns rows (t_sec, op, ms, ok) and the keys written.
    """
    rng = random.Random(seed)
    keys = [PREFIX + n for n in dataset_files(directory)]
    size = int(sum(os.path.getsize(os.path.join(directory, n)) for n in dataset_files(directory)) / len(keys))
    payload_rng = random.Random(seed + 1)
    rows, written = [], []
    t_start = time.perf_counter()
    n_write = 0
    while True:
        t = time.perf_counter() - t_start
        if t >= warmup_sec + duration_sec:
            break
        if rng.randint(1, 100) <= read_pct:
            ms, _, ok = store.get(rng.choice(keys))
            op = "read"
        else:
            key = f"bench/w_{n_write:06d}"
            data = payload_rng.randbytes(size)
            ms, _, ok = store.put(key, data)
            written.append(key)
            n_write += 1
            op = "write"
        if t >= warmup_sec:
            rows.append((round(t - warmup_sec, 4), op, ms, ok))
    return rows, written


def summarize_rows(rows, lat_idx, ok_idx, op=None, op_idx=None):
    """Latency summary of the successful rows (optionally one operation type) plus a failure count."""
    def keep(r):
        return op is None or r[op_idx] == op
    s = summarize([r[lat_idx] for r in rows if keep(r) and r[ok_idx]])
    s["failed"] = sum(1 for r in rows if keep(r) and not r[ok_idx])
    return s
