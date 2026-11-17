# Replication vs. erasure coding for DICOM objects on MinIO

Benchmark code for the paper "Performance and Storage Trade-offs of Replication and Erasure Coding for
Medical Imaging Workloads". **This branch fixes the benchmark; the paper's numbers have not been regenerated
yet.** Run the experiment (below) and take every number in the paper from `bench.aggregate`.

## What was wrong in the first version (see `legacy/`)

| Problem | Evidence in the old files | Fix |
|---|---|---|
| "Replication-3" was not replication | `docker-compose-repl3.yml` was either 3 unconnected single-drive servers or a 5 x 1-drive erasure cluster with default parity; MinIO has no replicated storage class | Replication is explicit and client-side: three independent single-drive servers, the client writes every object to all three (`compose/repl3.yml`, `bench/common.py: Store`) |
| `EC:4` is not "4+2" | `EC:N` is N *parity* shards over the *whole erasure set*: on 10 drives `EC:4` is 6+4, and the old `EC:5` was 5+5 | Layout matches the name: 4+2 on 6 drives, 5+2 on 7 drives (`compose/ec6.yml`, `ec7.yml`); a parity sweep on 10 drives is separate (`compose/ec10.yml`) |
| `EC:6` / `EC:8` configurations | Parity cannot exceed half the set (5 on 10 drives); the servers never started | Removed |
| Layout never checked | `cluster_report.sh` did not inspect parity or set size | `bench/layout.py` reads `mc admin info --json` and **aborts the run** if drives-per-set or parity differ from the configuration |
| Overhead computed from a formula | Hardcoded 200/50/40 in `collect_comparison_results.py` | Measured: apparent bytes on disk under the data directory before and after the upload (`du -sb` equivalent) |
| Different MinIO images | Baseline pinned `RELEASE.2024-12-13`, the EC files used `minio/minio:latest` | One pinned image in `configs.json`, used by every file |
| Text and table disagreed | The collector's regex took node 1's numbers (50 reads) for the text, the table used the cluster total (250 reads) | Raw per-operation CSVs; `bench.aggregate` writes the table *and* `numbers.tex` macros for the text |
| Read-only vs mixed latency gap | Read-only: 5 concurrent threads over 50 objects; mixed: 1 thread rereading the first 10 listed keys; no warm-up | Same client, sequential by default, random reads over all objects, warm-up discarded, same procedure in both workloads |
| Percentile definition | `statistics.quantiles` (exclusive) vs. nearest-rank in the paper | Nearest-rank everywhere (`bench/common.py: percentile`) |
| Writes were constant bytes, 100 KB | `b'X' * 102400` | Random bytes, same size as the dataset objects |
| Objects 4x smaller than a CT slice | 256 x 256 x 16 bit = 129 KB | 512 x 512 x 16 bit = 513 KB (`bench/dataset.py`) |
| No failure test | none | `--failure`: 0, 1, 2 nodes stopped, reads through survivors, recovery time |
| One run, no intervals | | `repetitions` fresh clusters per configuration, mean and 95 % interval |

The old results are kept in `legacy/results_invalid_configs/` for the record only. Do not cite them.

## Run

```bash
pip install -r requirements.txt            # needs Docker (compose v2) and the MinIO client `mc` on PATH
python -m bench.dataset                    # 100 synthetic CT slices, 512x512x16 bit -> dicom_files/
python -m unittest discover -s tests       # checks that need no Docker
python -m bench.run_all --configs ec10-6+4 --reps 1 --quick      # smoke test of the whole pipeline
python -m bench.run_all --failure          # full run: all configurations x 5 repetitions (hours)
python -m bench.aggregate results/<run_id> # -> summary.csv, table_x.tex, numbers.tex
```

Configurations (`configs.json`): `ec-4+2` (6 drives), `ec-5+2` (7 drives), `ec10-8+2`, `ec10-7+3`, `ec10-6+4`
(parity sweep on the original 5-node, 10-drive cluster) and `repl-3` (client-side replication).
`python -m bench.make_compose` regenerates the compose files.

## Limits to state in the paper

* Everything runs in containers on one laptop: no real network, shared CPU and disk.
* The 4+2, 5+2 and replication clusters have different node counts (3, 7, 3). Only the 10-drive parity sweep
  holds the hardware layout fixed; use it to separate the effect of parity from the effect of cluster size.
* Replication is emulated by the client (parallel writes, read from a random replica). It is not a MinIO feature.
* Synthetic pixel data; file content does not matter for storage cost, but it does for any compression.
* `mc admin info` JSON keys and the `docker compose stop/start` failure test were written against the documented
  behaviour and could not be run in the environment where this branch was prepared (no Docker daemon); the
  `--quick` run is the first thing to try. Data directories are created by Docker and may need `sudo` to delete on Linux.
