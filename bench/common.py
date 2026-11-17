"""Shared helpers: configuration, S3 clients, statistics.

Design rules (they fix problems found in the first version of this benchmark):
  * one boto3 client per endpoint, created once and reused;
  * percentiles use the nearest-rank definition stated in the paper;
  * every latency is written to disk, nothing is parsed back out of printed text;
  * "replication" is explicit client-side 3x replication (MinIO has no replicated storage class).
"""
import json
import math
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# two-sided 95% Student t critical values by degrees of freedom
_T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262,
         10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110,
         18: 2.101, 19: 2.093, 20: 2.086, 25: 2.060, 30: 2.042}


def t_crit(df):
    if df < 1:
        return float("nan")
    if df in _T975:
        return _T975[df]
    keys = sorted(_T975)
    for k in keys:
        if k >= df:
            return _T975[k]
    return 1.96


def percentile(values, p):
    """Nearest-rank percentile: the ceil(p/100 * n)-th smallest value (p in 0..100)."""
    if not values:
        return float("nan")
    xs = sorted(values)
    rank = max(1, math.ceil(p / 100.0 * len(xs)))
    return xs[rank - 1]


def summarize(latencies):
    if not latencies:
        return {"n": 0, "mean": float("nan"), "p50": float("nan"), "p95": float("nan"),
                "p99": float("nan"), "min": float("nan"), "max": float("nan")}
    return {"n": len(latencies), "mean": sum(latencies) / len(latencies),
            "p50": percentile(latencies, 50), "p95": percentile(latencies, 95),
            "p99": percentile(latencies, 99), "min": min(latencies), "max": max(latencies)}


def mean_ci(xs):
    """Mean and 95% confidence half-width across repetitions (nan half-width for one run)."""
    xs = [x for x in xs if x is not None and not math.isnan(x)]
    n = len(xs)
    if n == 0:
        return float("nan"), float("nan")
    m = sum(xs) / n
    if n == 1:
        return m, float("nan")
    var = sum((x - m) ** 2 for x in xs) / (n - 1)
    return m, t_crit(n - 1) * math.sqrt(var / n)


def load_settings(path=None):
    path = path or os.path.join(ROOT, "configs.json")
    with open(path) as f:
        return json.load(f)


def node_ports(cfg):
    return [9100 + i for i in range(1, cfg["nodes"] + 1)]


def endpoints(cfg):
    return [f"http://localhost:{p}" for p in node_ports(cfg)]


def make_client(endpoint, user, password):
    import boto3
    from botocore.config import Config
    return boto3.client(
        "s3", endpoint_url=endpoint, aws_access_key_id=user, aws_secret_access_key=password,
        region_name="us-east-1", use_ssl=False,
        config=Config(retries={"max_attempts": 1, "mode": "standard"}, max_pool_connections=16,
                      connect_timeout=5, read_timeout=30, s3={"addressing_style": "path"}))


class Store:
    """Uniform put/get over a configuration.

    type "ec":          every node is a gateway to the same erasure-coded cluster; operations are
                        spread round-robin over the nodes that are up.
    type "replication": independent single-drive servers. put() writes the object to every replica
                        in parallel and returns when all have acknowledged; get() reads from a
                        random replica and falls back to the others if it fails.
    """

    def __init__(self, cfg, settings, client_factory=None, alive=None, seed=0):
        self.cfg = cfg
        self.bucket = settings["bucket"]
        factory = client_factory or (lambda ep: make_client(ep, settings["user"], settings["password"]))
        self.endpoints = endpoints(cfg)
        self.clients = {ep: factory(ep) for ep in self.endpoints}
        self.alive = list(alive) if alive is not None else list(self.endpoints)
        self.type = cfg["type"]
        self.rng = random.Random(seed)
        self._rr = 0
        self._pool = ThreadPoolExecutor(max_workers=max(1, len(self.endpoints)))

    # -- helpers ------------------------------------------------------------
    def ensure_bucket(self):
        for ep in self.alive:
            try:
                self.clients[ep].create_bucket(Bucket=self.bucket)
            except Exception as e:  # already exists is fine; anything else surfaces on first put
                if "BucketAlready" not in str(e):
                    pass
            if self.type == "ec":
                break

    def _next_ec_endpoint(self):
        ep = self.alive[self._rr % len(self.alive)]
        self._rr += 1
        return ep

    # -- operations: return (latency_ms or None, endpoint, ok) -------------------
    def put(self, key, data):
        t0 = time.perf_counter()
        if self.type == "ec":
            ep = self._next_ec_endpoint()
            try:
                self.clients[ep].put_object(Bucket=self.bucket, Key=key, Body=data)
                ok = True
            except Exception:
                ok = False
            return (time.perf_counter() - t0) * 1000, ep, ok
        futures = [(ep, self._pool.submit(self.clients[ep].put_object, Bucket=self.bucket, Key=key, Body=data))
                   for ep in self.alive]
        ok = True
        for ep, fu in futures:
            try:
                fu.result()
            except Exception:
                ok = False
        return (time.perf_counter() - t0) * 1000, "all", ok

    def get(self, key):
        if self.type == "ec":
            order = [self._next_ec_endpoint()]
        else:
            order = self.rng.sample(self.alive, len(self.alive))
        t0 = time.perf_counter()
        for ep in order:
            try:
                resp = self.clients[ep].get_object(Bucket=self.bucket, Key=key)
                resp["Body"].read()
                return (time.perf_counter() - t0) * 1000, ep, True
            except Exception:
                continue
        return (time.perf_counter() - t0) * 1000, order[-1], False

    def delete(self, key):
        for ep in (self.alive if self.type != "ec" else self.alive[:1]):
            try:
                self.clients[ep].delete_object(Bucket=self.bucket, Key=key)
            except Exception:
                pass


def dataset_files(directory):
    return sorted(f for f in os.listdir(directory) if f.endswith(".dcm"))


def write_csv(path, header, rows):
    import csv
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
