"""Runs the case study on every graph and collects the results.

Usage (from src/):  python run_all.py [--dir ..] [--searches 100] [--exact-max-n 20000]
Each (graph, representation) runs in its own process, so memory is measured
cleanly. The adjacency matrix is skipped when n^2 bytes would not fit in RAM.
Outputs: results/<graph>_<rep>.json, results/results.csv, results/results.md
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import time


def available_ram_bytes() -> int:
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemAvailable"):
                return int(line.split()[1]) * 1024


def read_n(path: str) -> int:
    with open(path) as f:
        return int(f.readline())


def save(rows, out):
    cols = ["graph", "representation", "status", "n", "m", "memory_mb", "searches",
            "bfs_mean_s", "dfs_mean_s", "components", "largest", "smallest",
            "diameter_approx", "diameter_approx_s", "diameter_exact", "diameter_exact_s", "stages_done"]
    with open(os.path.join(out, "results.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(out, "results.md"), "w") as f:
        f.write("| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n")
        for r in rows:
            f.write("| " + " | ".join(
                f"{r[c]:.4g}" if isinstance(r.get(c), float)
                else " ".join(x.split("_")[0] for x in r[c]) if c == "stages_done" and c in r
                else str(r.get(c, "")) for c in cols) + " |\n")
    # keep the case-study details that are not tabular
    with open(os.path.join(out, "results.json"), "w") as f:
        json.dump(rows, f, indent=2)


def load_partial(out_json, row):
    """Merge whatever the run managed to record before it died."""
    if os.path.exists(out_json):
        with open(out_json) as f:
            row.update(json.load(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="..")
    ap.add_argument("--searches", type=int, default=100)
    ap.add_argument("--exact-max-n", type=int, default=20000,
                    help="compute the exact diameter only when n <= this value")
    ap.add_argument("--timeout", type=int, default=3600,
                    help="max seconds per (graph, representation) run; it is marked 'timeout' if exceeded")
    ap.add_argument("--out", default="results")
    ap.add_argument("--graphs", nargs="*", type=int, default=[1, 2, 3, 4, 5, 6])
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rows = []

    for i in a.graphs:
        path = os.path.join(a.dir, f"grafo_{i}.txt")
        n = read_n(path)
        for rep in ("list", "matrix"):
            name = f"graph_{i}_{rep}"
            row = {"graph": i, "representation": rep, "n": n}
            if rep == "matrix" and n * n > 0.8 * available_ram_bytes():
                row["status"] = f"skipped: matrix needs ~{n * n / 2**30:.1f} GiB"
                print(f"[{name}] {row['status']}")
                rows.append(row)
                save(rows, a.out)
                continue
            out_json = os.path.join(a.out, f"{name}.json")
            cmd = [sys.executable, "case_study.py", path, "--searches", str(a.searches),
                   "--output", os.path.join(a.out, name), "--json", out_json]
            if rep == "matrix":
                cmd.append("--matrix")
            if rep == "list" and n <= a.exact_max_n:
                cmd.append("--exact-diameter")
            print(f"[{name}] running...", flush=True)
            t = time.time()
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=a.timeout)
            except subprocess.TimeoutExpired:
                load_partial(out_json, row)
                row["status"] = f"timeout (> {a.timeout} s) at {row.get('stage_running')}"
                print(f"[{name}] {row['status']}", flush=True)
                rows.append(row)
                save(rows, a.out)
                continue
            with open(os.path.join(a.out, f"{name}.log"), "w") as f:
                f.write(proc.stdout + proc.stderr)
            if proc.returncode != 0 or not os.path.exists(out_json):
                load_partial(out_json, row)
                row["status"] = f"failed at {row.get('stage_running')} (see .log)"
            else:
                load_partial(out_json, row)
                row["status"] = "ok" if row.get("finished") else "incomplete"
            print(f"[{name}] {row['status']} in {time.time() - t:.0f} s", flush=True)
            rows.append(row)
            save(rows, a.out)

    save(rows, a.out)
    print(f"\nDone. Send me {a.out}/results.md (and results.json).")


if __name__ == "__main__":
    main()
