# Legacy files (first version of the study)

These files produced the numbers in the first submitted version of the paper. They are kept for the record.

* The "Replication-3" results were measured on a 5-node cluster (all five endpoints answered), not on three
  replicas; the replication compose file in the git history is three unconnected single-drive servers, and an
  earlier local version was a 5 x 1-drive erasure cluster with default parity. In neither case was data replicated.
* "EC-4+2" ran `EC:4` and "EC-5+2" ran `EC:5` on 10 drives, which is 6+4 and 5+5.
* `docker-compose-ec62*.yml` and `docker-compose-ec82.yml` set parity above half of the 10-drive set; the servers
  did not start, so `results_invalid_configs/ec62_*` contain connection errors and `ec82_*` are empty.
* The baseline compose file pinned `RELEASE.2024-12-13`; the erasure-coded ones used `minio/minio:latest`.
* `collect_comparison_results.py` read the first `Mean:` line of each result file (node 1 only).

Do not cite numbers from `results_invalid_configs/`. Use `bench/` and `configs.json` instead.
