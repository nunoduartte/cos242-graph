"""Recomputes only stage 7 (approximate diameter, now per component) and updates
results/results.json, results.csv and results.md.

Usage (from src/):  python rerun_diameter.py [--graphs 1 2 3 4 5 6] [--dir ..] [--results results]
"""
import argparse
import json
import os
import time

from graphs import ApproximateDiameter, GraphReader
from run_all import save


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="..")
    ap.add_argument("--results", default="results")
    ap.add_argument("--graphs", nargs="*", type=int, default=[1, 2, 3, 4, 5, 6])
    a = ap.parse_args()

    path = os.path.join(a.results, "results.json")
    with open(path) as f:
        rows = json.load(f)

    for i in a.graphs:
        print(f"[graph_{i}] loading...", flush=True)
        g = GraphReader.read(os.path.join(a.dir, f"grafo_{i}.txt"), "list")
        t = time.perf_counter()
        d = g.diameter(ApproximateDiameter())
        elapsed = time.perf_counter() - t
        for r in rows:
            if r["graph"] == i and r.get("diameter_approx") is not None:
                print(f"[graph_{i}] {r['representation']}: old={r['diameter_approx']} new={d}")
                r["diameter_approx"] = d
                if r["representation"] == "list":
                    r["diameter_approx_s"] = elapsed
        print(f"[graph_{i}] diameter >= {d} ({elapsed:.1f} s)", flush=True)
        save(rows, a.results)  # incremental, like run_all.py

    print(f"\nDone. Send me {a.results}/results.md")


if __name__ == "__main__":
    main()
