"""Case studies for Part 1.

Usage: python case_study.py graph.txt [--matrix] [--exact-diameter]
One representation per run, so the measured memory is fair.
"""
import argparse
import json
import os
import random
import time

from graphs import (BFS, DFS, ApproximateDiameter, ExactDiameter,
                    GraphReader, ReportWriter)


def rss_mb() -> float:
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS"):
                return int(line.split()[1]) / 1024


def mean_time(search, graph, starts) -> float:
    t = time.perf_counter()
    for s in starts:
        search.run(graph, s)
    return (time.perf_counter() - t) / len(starts)


class Recorder:
    """Keeps the metrics and saves them to JSON after every stage, so a crash or
    timeout still leaves a record of what finished and where it got stuck."""

    def __init__(self, path, base):
        self.path = path
        self.data = dict(base, stages_done=[], stage_running=None)
        self._t0 = time.perf_counter()
        self._save()

    def start(self, stage):
        self.data["stage_running"] = stage
        self._save()

    def done(self, stage, **metrics):
        self.data.update(metrics)
        self.data["stages_done"].append(stage)
        self.data["stage_running"] = None
        self.data.setdefault("stage_seconds", {})[stage] = time.perf_counter() - self._t0
        self._t0 = time.perf_counter()
        self._save()

    def _save(self):
        if self.path:
            with open(self.path, "w") as f:
                json.dump(self.data, f, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--matrix", action="store_true")
    ap.add_argument("--searches", type=int, default=100)
    ap.add_argument("--exact-diameter", action="store_true")
    ap.add_argument("--output", default="output")
    ap.add_argument("--json", help="write the collected metrics to this JSON file")
    a = ap.parse_args()
    rep = "matrix" if a.matrix else "list"
    os.makedirs(a.output, exist_ok=True)
    rec = Recorder(a.json, {"file": a.file, "representation": rep})

    rec.start("1_load_memory")
    base = rss_mb()
    g = GraphReader.read(a.file, rep)
    rec.done("1_load_memory", n=g.n, m=g.m, memory_mb=rss_mb() - base, rss_total_mb=rss_mb())
    print(f"[1] {rep}: memory ~ {rec.data['memory_mb']:.1f} MB (total RSS {rec.data['rss_total_mb']:.1f} MB)", flush=True)

    searches = (BFS(), DFS())
    starts = random.Random(42).sample(g.vertices(), min(a.searches, g.n))
    for s, stage in zip(searches, ("2_bfs_time", "3_dfs_time")):
        rec.start(stage)
        mean = mean_time(s, g, starts)
        rec.done(stage, **{f"{s.name.lower()}_mean_s": mean}, searches=len(starts))
        print(f"[{stage[0]}] {s.name}: mean time = {mean:.6f} s ({len(starts)} searches)", flush=True)

    rec.start("4_parents")
    parents = {}
    for root in (1, 2, 3):
        for s in searches:
            r = g.search(root, s)
            parents[f"{s.name} root {root}"] = {v: r.parent[v] for v in (10, 20, 30)}
            print(f"[4] {s.name} root {root}: " + ", ".join(f"parent({v})={r.parent[v]}" for v in (10, 20, 30)), flush=True)
            ReportWriter.tree(r, s.name, f"{a.output}/{s.name.lower()}_{root}.txt")
    rec.done("4_parents", parents=parents)

    rec.start("5_distances")
    distances = {f"{u}-{v}": g.distance(u, v) for u, v in ((10, 20), (10, 30), (20, 30))}
    rec.done("5_distances", distances=distances)
    print("[5] Distances:", distances, flush=True)

    rec.start("6_components")
    comps = g.connected_components()
    rec.done("6_components", components=len(comps), largest=len(comps[0]), smallest=len(comps[-1]))
    print(f"[6] Components: {len(comps)}; largest={len(comps[0])}; smallest={len(comps[-1])}", flush=True)
    rec.start("6b_summary_file")
    ReportWriter.summary(g, f"{a.output}/summary.txt", comps)
    rec.done("6b_summary_file")

    rec.start("7_diameter_approx")
    d = g.diameter(ApproximateDiameter())
    rec.done("7_diameter_approx", diameter_approx=d)
    print(f"[7] Approximate diameter >= {d} ({rec.data['stage_seconds']['7_diameter_approx']:.2f} s)", flush=True)
    rec.data["diameter_approx_s"] = rec.data["stage_seconds"]["7_diameter_approx"]
    if a.exact_diameter:
        rec.start("7b_diameter_exact")
        d = g.diameter(ExactDiameter())
        rec.done("7b_diameter_exact", diameter_exact=d)
        rec.data["diameter_exact_s"] = rec.data["stage_seconds"]["7b_diameter_exact"]
        print(f"[7] Exact diameter = {d} ({rec.data['diameter_exact_s']:.1f} s)", flush=True)
    rec.data["finished"] = True
    rec._save()


if __name__ == "__main__":
    main()
