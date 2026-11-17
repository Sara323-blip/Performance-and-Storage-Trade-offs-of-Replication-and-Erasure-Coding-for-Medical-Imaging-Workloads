"""Unit tests for the parts that do not need Docker: statistics, store logic, layout checks, aggregation.

Run: python -m unittest discover -s tests -v
"""
import csv
import json
import math
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bench import aggregate, layout  # noqa: E402
from bench.common import Store, mean_ci, percentile, summarize  # noqa: E402

SETTINGS = {"bucket": "b", "user": "u", "password": "p"}


class FakeClient:
    def __init__(self, fail=False):
        self.fail, self.objects = fail, {}

    def put_object(self, Bucket, Key, Body):
        if self.fail:
            raise RuntimeError("down")
        self.objects[Key] = Body

    def get_object(self, Bucket, Key):
        if self.fail or Key not in self.objects:
            raise RuntimeError("down or missing")
        body = self.objects[Key]

        class B:
            def read(self_inner):
                return body
        return {"Body": B()}

    def delete_object(self, Bucket, Key):
        self.objects.pop(Key, None)

    def create_bucket(self, Bucket):
        pass


class Percentiles(unittest.TestCase):
    def test_nearest_rank(self):
        xs = list(range(1, 101))                 # 1..100
        self.assertEqual(percentile(xs, 95), 95)  # ceil(0.95*100)=95th smallest
        self.assertEqual(percentile(xs, 99), 99)
        self.assertEqual(percentile(xs, 50), 50)
        self.assertEqual(percentile([5], 95), 5)
        self.assertEqual(percentile([3, 1, 2], 100), 3)

    def test_matches_paper_definition_on_small_sample(self):
        xs = [10, 20, 30, 40]
        self.assertEqual(percentile(xs, 95), 40)  # ceil(0.95*4)=4

    def test_summarize(self):
        s = summarize([1.0, 2.0, 3.0, 4.0])
        self.assertAlmostEqual(s["mean"], 2.5)
        self.assertEqual((s["min"], s["max"]), (1.0, 4.0))

    def test_mean_ci(self):
        m, ci = mean_ci([10.0, 12.0, 14.0])
        self.assertAlmostEqual(m, 12.0)
        self.assertAlmostEqual(ci, 4.303 * 2.0 / math.sqrt(3), places=3)   # t(2)=4.303, sd=2
        self.assertTrue(math.isnan(mean_ci([5.0])[1]))


class StoreLogic(unittest.TestCase):
    def make(self, typ, nodes, down=()):
        cfg = {"type": typ, "nodes": nodes}
        clients = {}

        def factory(ep):
            clients[ep] = FakeClient(fail=ep in down)
            return clients[ep]
        eps = [f"http://localhost:{9100 + i}" for i in range(1, nodes + 1)]
        down_eps = [e for e in eps if e in down]
        store = Store(cfg, SETTINGS, client_factory=factory, alive=[e for e in eps if e not in down_eps])
        return store, clients

    def test_replication_writes_all_copies(self):
        store, clients = self.make("replication", 3)
        ms, ep, ok = store.put("k", b"data")
        self.assertTrue(ok)
        self.assertEqual(sum(1 for c in clients.values() if "k" in c.objects), 3)

    def test_replication_read_falls_back(self):
        store, clients = self.make("replication", 3)
        store.put("k", b"data")
        store.alive = list(store.endpoints)       # all nominally alive...
        first = store.endpoints[0]
        clients[first].fail = True                # ...but one replica starts failing
        for _ in range(20):
            _, _, ok = store.get("k")
            self.assertTrue(ok)

    def test_ec_round_robin(self):
        store, clients = self.make("ec", 3)
        for i in range(6):
            store.put(f"k{i}", b"x")
        self.assertEqual([len(c.objects) for c in clients.values()], [2, 2, 2])

    def test_ec_get_reports_failure(self):
        store, _ = self.make("ec", 3)
        _, _, ok = store.get("missing")
        self.assertFalse(ok)


class Layout(unittest.TestCase):
    INFO = {"info": {"backend": {"backendType": "Erasure", "onlineDisks": 10, "offlineDisks": 0,
                                 "standardSCParity": 4, "rrSCParity": 1,
                                 "totalSets": [1], "totalDrivesPerSet": [10]}}}

    def test_read_layout(self):
        lay = layout.read_layout(self.INFO)
        self.assertEqual((lay["drives_per_set"], lay["standard_parity"], lay["sets"]), (10, 4, 1))

    def test_check_detects_the_original_misconfiguration(self):
        # "EC:4 = 4 data + 2 parity" on 10 drives was really 6 data + 4 parity
        cfg = {"type": "ec", "drives": 6, "m": 2}
        problems = layout.check_layout(cfg, layout.read_layout(self.INFO))
        self.assertEqual(len(problems), 2)
        cfg_ok = {"type": "ec", "drives": 10, "m": 4}
        self.assertEqual(layout.check_layout(cfg_ok, layout.read_layout(self.INFO)), [])

    def test_overhead_and_dir_bytes(self):
        self.assertAlmostEqual(layout.overhead(1000, 1000 + 1500, 1000), 50.0)
        self.assertAlmostEqual(layout.overhead(0, 3000, 1000), 200.0)
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "a"))
            for name, n in (("f1", 100), ("a/f2", 250)):
                with open(os.path.join(d, name), "wb") as f:
                    f.write(b"x" * n)
            self.assertEqual(layout.dir_bytes(d), 350)


class Aggregate(unittest.TestCase):
    def write_rep(self, base, cfg, rep, read_ms, write_ms, overhead):
        d = os.path.join(base, cfg, f"rep{rep}")
        os.makedirs(d)
        with open(os.path.join(d, "read.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["i", "key", "endpoint", "ms", "ok"])
            for i, ms in enumerate(read_ms):
                w.writerow([i, "k", "e", ms, True])
        with open(os.path.join(d, "mixed.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t_sec", "op", "ms", "ok"])
            for i in range(10):
                w.writerow([i, "read", 5.0, True])
            for ms in write_ms:
                w.writerow([1, "write", ms, True])
        with open(os.path.join(d, "overhead.json"), "w") as f:
            json.dump({"overhead_pct": overhead}, f)

    def test_aggregate_and_outputs(self):
        with tempfile.TemporaryDirectory() as base:
            for rep, shift in ((1, 0), (2, 2)):
                self.write_rep(base, "repl-3", rep, [10 + shift] * 20, [20.0] * 5, 200.0)
                self.write_rep(base, "ec-4+2", rep, [12 + shift] * 20, [30.0] * 5, 50.0)
            agg = aggregate.aggregate(base)
            self.assertEqual(agg["repl-3"]["n_reps"], 2)
            self.assertAlmostEqual(agg["repl-3"]["read_mean"][0], 11.0)
            aggregate.write_outputs(base, agg, {"repl-3": "Replication x3", "ec-4+2": "EC 4+2"}, "repl-3")
            table = open(os.path.join(base, "table_x.tex")).read()
            self.assertIn("EC 4+2", table)
            nums = open(os.path.join(base, "numbers.tex")).read()
            self.assertIn(r"\newcommand{\EcFourPTwoReadMean}{13.0}", nums)
            self.assertIn(r"\EcFourPTwoReadMeanVsBasePct}{+18}", nums)   # 13/11 - 1 = +18 %
            self.assertTrue(os.path.exists(os.path.join(base, "summary.csv")))


if __name__ == "__main__":
    unittest.main()
