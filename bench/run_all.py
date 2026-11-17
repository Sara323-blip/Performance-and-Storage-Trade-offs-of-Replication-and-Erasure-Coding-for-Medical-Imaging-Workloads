"""Run the whole experiment: for every configuration and repetition start a fresh cluster, verify its layout,
upload, measure on-disk overhead, run read-only and mixed workloads, optionally test failures, tear down.

  python -m bench.run_all --configs ec-4+2 ec-5+2 repl-3 --reps 5 --failure
  python -m bench.run_all --configs ec10-6+4 --reps 1 --quick        # smoke test, short workloads

Results go to results/<run_id>/<config>/rep<k>/ as CSV/JSON. Then: python -m bench.aggregate results/<run_id>
Requires Docker (compose v2) and the MinIO client `mc` on PATH.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time

from . import layout
from .common import ROOT, Store, endpoints, load_settings, node_ports, summarize, write_csv
from .workloads import mixed_workload, raw_bytes, read_workload, summarize_rows, upload_dataset


def compose(cfg, settings, data_dir, project, *args):
    env = dict(os.environ, MINIO_IMAGE=settings["image"], DATA_DIR=data_dir,
               MINIO_ROOT_USER=settings["user"], MINIO_ROOT_PASSWORD=settings["password"], **cfg.get("env", {}))
    cmd = ["docker", "compose", "-f", os.path.join(ROOT, cfg["compose"]), "-p", project, *args]
    return subprocess.run(cmd, env=env, capture_output=True, text=True)


def wait_ready(cfg, settings, timeout=240):
    """Wait until every drive is online (EC) or every server answers (replication)."""
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout:
        try:
            if cfg["type"] == "ec":
                info = layout.read_layout(layout.mc_info(endpoints(cfg)[0], settings["user"], settings["password"]))
                if info["online_drives"] == cfg["drives"] and info["drives_per_set"]:
                    return time.time() - t0
                last = info
            else:
                from .common import make_client
                for ep in endpoints(cfg):
                    make_client(ep, settings["user"], settings["password"]).list_buckets()
                return time.time() - t0
        except Exception as e:  # not up yet
            last = str(e)
        time.sleep(2)
    raise TimeoutError(f"cluster not ready after {timeout}s: {last}")


def failure_test(cfg, settings, data_dir, project, directory, out_dir, n_reads, down_counts, seed):
    """Stop 0, 1, 2 nodes, run reads through the survivors, then restart and time recovery."""
    rows = []
    eps = endpoints(cfg)
    services = [f"minio{i}" for i in range(1, cfg["nodes"] + 1)]
    for down in down_counts:
        if down >= cfg["nodes"]:
            continue
        if down:
            compose(cfg, settings, data_dir, project, "stop", *services[-down:])
            time.sleep(5)
        alive = eps[: len(eps) - down]
        store = Store(cfg, settings, alive=alive, seed=seed)
        res = read_workload(store, directory, n_reads, warmup=0, seed=seed + down)
        s = summarize_rows(res, lat_idx=3, ok_idx=4)
        rows.append((down, down * (cfg["drives"] // cfg["nodes"]), s["n"], s["failed"], s["mean"], s["p95"]))
        if down:
            compose(cfg, settings, data_dir, project, "start", *services[-down:])
            t0 = time.time()
            wait_ready(cfg, settings)
            rows[-1] = rows[-1] + (round(time.time() - t0, 1),)
        else:
            rows[-1] = rows[-1] + (0.0,)
    write_csv(os.path.join(out_dir, "failure.csv"),
              ["nodes_down", "drives_down", "reads_ok", "reads_failed", "mean_ms", "p95_ms", "recovery_sec"], rows)


def run_one(name, cfg, settings, rep, run_dir, args):
    directory = os.path.join(ROOT, settings["dataset_dir"])
    out_dir = os.path.join(run_dir, name, f"rep{rep}")
    data_dir = os.path.join(ROOT, "data", name, f"rep{rep}")
    project = f"mb_{name}_{rep}".replace("+", "p").replace("-", "_")
    shutil.rmtree(data_dir, ignore_errors=True)
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)
    compose(cfg, settings, data_dir, project, "down", "-v")
    up = compose(cfg, settings, data_dir, project, "up", "-d")
    if up.returncode != 0:
        raise RuntimeError(f"compose up failed for {name}: {up.stderr}")
    try:
        t_ready = wait_ready(cfg, settings)
        info = {}
        if cfg["type"] == "ec":
            raw = layout.mc_info(endpoints(cfg)[0], settings["user"], settings["password"])
            info = layout.read_layout(raw)
            with open(os.path.join(out_dir, "layout.json"), "w") as f:
                json.dump({"layout": info, "raw": raw, "image": settings["image"]}, f, indent=1)
            problems = layout.check_layout(cfg, info)
            if problems:
                raise RuntimeError(f"{name}: layout does not match the configuration: {'; '.join(problems)}")
        store = Store(cfg, settings, seed=rep)
        before = layout.dir_bytes(data_dir)
        up_rows = upload_dataset(store, directory)
        write_csv(os.path.join(out_dir, "upload.csv"), ["key", "ms", "ok"], up_rows)
        if not all(r[2] for r in up_rows):
            raise RuntimeError(f"{name}: some uploads failed")
        time.sleep(2)                                     # let MinIO finish writing metadata
        after = layout.dir_bytes(data_dir)
        raw = raw_bytes(directory)
        with open(os.path.join(out_dir, "overhead.json"), "w") as f:
            json.dump({"before_bytes": before, "after_bytes": after, "raw_bytes": raw,
                       "overhead_pct": layout.overhead(before, after, raw), "ready_sec": t_ready}, f, indent=1)

        r = dict(settings["read"])
        if args.quick:
            r.update(reads=20, warmup=5)
        rows = read_workload(store, directory, r["reads"], r["warmup"], r["seed"] + rep, r["concurrency"])
        write_csv(os.path.join(out_dir, "read.csv"), ["i", "key", "endpoint", "ms", "ok"], rows)

        m = dict(settings["mixed"])
        if args.quick:
            m.update(duration_sec=10, warmup_sec=2)
        mrows, written = mixed_workload(store, directory, m["duration_sec"], m["warmup_sec"], m["read_pct"], m["seed"] + rep)
        write_csv(os.path.join(out_dir, "mixed.csv"), ["t_sec", "op", "ms", "ok"], mrows)
        for k in written:
            store.delete(k)

        if args.failure:
            f = dict(settings["failure"])
            failure_test(cfg, settings, data_dir, project, directory, out_dir, 20 if args.quick else f["reads"],
                         f["down_counts"], rep)
    finally:
        compose(cfg, settings, data_dir, project, "down", "-v")
        if not args.keep_data:
            shutil.rmtree(data_dir, ignore_errors=True)


def main():
    settings = load_settings()
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", nargs="+", default=list(settings["configs"]))
    ap.add_argument("--reps", type=int, default=settings["repetitions"])
    ap.add_argument("--failure", action="store_true", help="also run the node-failure test")
    ap.add_argument("--quick", action="store_true", help="short workloads, for checking that the setup works")
    ap.add_argument("--keep-data", action="store_true")
    ap.add_argument("--run-id", default=time.strftime("%Y%m%d-%H%M%S"))
    args = ap.parse_args()

    if not os.path.isdir(os.path.join(ROOT, settings["dataset_dir"])):
        sys.exit(f"missing {settings['dataset_dir']}/ - run: python -m bench.dataset")
    for tool in ("docker", "mc"):
        if shutil.which(tool) is None:
            sys.exit(f"`{tool}` not found on PATH")
    run_dir = os.path.join(ROOT, "results", args.run_id)
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, "run.json"), "w") as f:
        json.dump({"image": settings["image"], "configs": args.configs, "reps": args.reps,
                   "quick": args.quick, "settings": settings}, f, indent=1)
    for name in args.configs:
        for rep in range(1, args.reps + 1):
            print(f"=== {name} repetition {rep}/{args.reps} ===", flush=True)
            run_one(name, settings["configs"][name], settings, rep, run_dir, args)
    print(f"done. Next: python -m bench.aggregate results/{args.run_id}")


if __name__ == "__main__":
    main()
