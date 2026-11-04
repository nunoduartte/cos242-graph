"""Case study B: mean time of Dijkstra from one source to all vertices, vector x heap.

Usage (from the repository root):
  python -m experiments.benchmark [--data-dir ../T2] [--graphs grafo_W_3 ...] [--k 100] [--seed 42]
                                  [--strategies vector heap] [--budget 1200] [--run-timeout 900]
For each graph, k distinct sources are drawn with the seed and both strategies
run from the same sources, in the same order. Only the Dijkstra call is timed
(time.perf_counter), with the garbage collector paused, as timeit does.

The vector version is O(n^2): on the large graphs a single run can take hours
or days. So every run has a hard limit (--run-timeout) and each (graph,
strategy) a time budget (--budget); runs that do not fit are recorded as
"timeout" or "not run" and never estimated. The mean is over completed runs,
and the speedup only uses sources completed by both strategies.
Every run is saved as soon as it ends; --resume continues an interrupted
benchmark (same settings) without repeating finished runs.
Outputs: results/part2/benchmarks/<graph>.json, runs.csv, summary.csv, summary.md
"""
import argparse
import gc
import os
import random
import statistics
import time

from graphs import Dijkstra
from graphs.priority_queues import QUEUES

from .common import (DEFAULT_DATA_DIR, DEFAULT_RESULTS, WEIGHTED_GRAPHS, RunTimeout, environment,
                     graph_results, load, log, md_table, read_json, time_limit, write_csv, write_json)


def bench(g, name, strategy, sources, budget, run_timeout, runs, save):
    """Runs Dijkstra from each source until the budget ends, one record per source.

    `runs` holds the records already made for this strategy (empty, or a
    previous partial execution being resumed): they count toward the budget and
    are not repeated. save() is called after every record, so an interrupted
    benchmark loses at most the run in progress.
    """
    dijkstra = Dijkstra(QUEUES[strategy])
    spent = sum(r.get("seconds") or r.get("interrupted_after_s") or 0 for r in runs)
    for i, s in enumerate(sources[len(runs):], len(runs)):
        run = {"graph": name, "strategy": strategy, "run": i, "source": s, "seconds": None}
        longest = max((r["seconds"] for r in runs if r["seconds"] is not None), default=0)
        if any(r["status"].startswith("timeout") and r.get("limit_s", run_timeout) >= run_timeout
               for r in runs if run_timeout):
            # a run hit the hard limit: the next ones would too
            run["status"] = "not run (previous run timed out)"
        elif budget and (spent >= budget or budget - spent < longest):
            # skip a run that could not finish in what is left of the budget
            run["status"] = "not run (budget)"
        else:
            limits = [x for x in (run_timeout, budget - spent if budget else 0) if x]
            limit = min(limits) if limits else None
            gc.collect()
            gc.disable()
            t = time.perf_counter()
            try:
                with time_limit(limit):
                    dijkstra.run(g, s)
                run["seconds"] = time.perf_counter() - t
                run["status"] = "ok"
            except RunTimeout:
                run["status"] = f"timeout (> {limit:.0f} s)"
                run["interrupted_after_s"] = time.perf_counter() - t
                run["limit_s"] = limit
            finally:
                gc.enable()
            spent += time.perf_counter() - t
            log(f"{name} {strategy} #{i} source {s}: {run['status']}"
                + (f" {run['seconds']:.3f} s" if run["seconds"] is not None else ""))
        runs.append(run)
        save()
    return runs


def summarize(data):
    """Rows of the summary table for one graph."""
    by = {}
    for r in data["runs"]:
        by.setdefault(r["strategy"], []).append(r)
    out = {"graph": data["graph"], "n": data["n"], "m": data["m"], "k": data["k"], "seed": data["seed"]}
    done = {}
    for strategy, runs in by.items():
        times = [r["seconds"] for r in runs if r["status"] == "ok"]
        done[strategy] = {r["source"]: r["seconds"] for r in runs if r["status"] == "ok"}
        out[f"{strategy}_runs"] = len(times)
        out[f"{strategy}_mean_ms"] = statistics.fmean(times) * 1000 if times else None
        out[f"{strategy}_stdev_ms"] = statistics.stdev(times) * 1000 if len(times) > 1 else None
        stopped = [r for r in runs if r["status"].startswith("timeout")]
        out[f"{strategy}_note"] = stopped[0]["status"] if stopped and not times else ""
    if "vector" in done and "heap" in done:
        paired = [s for s in done["vector"] if s in done["heap"]]
        out["paired_runs"] = len(paired)
        if paired:
            v = statistics.fmean(done["vector"][s] for s in paired)
            h = statistics.fmean(done["heap"][s] for s in paired)
            out["speedup"] = v / h
    return out


def ms(x):
    return "-" if x is None else f"{x:,.1f}".replace(",", " ")


def write_tables(out):
    datas = graph_results(out)
    write_csv(os.path.join(out, "runs.csv"), [r for d in datas for r in d["runs"]],
              ["graph", "strategy", "run", "source", "seconds", "status", "interrupted_after_s"])
    rows = [summarize(d) for d in datas]
    cols = ["graph", "n", "m", "k", "seed", "vector_runs", "vector_mean_ms", "vector_stdev_ms", "vector_note",
            "heap_runs", "heap_mean_ms", "heap_stdev_ms", "heap_note", "paired_runs", "speedup"]
    write_csv(os.path.join(out, "summary.csv"), rows, cols)

    def cell(r, s):
        if r.get(f"{s}_mean_ms") is not None:
            return f"{ms(r[f'{s}_mean_ms'])} ({r[f'{s}_runs']}/{r['k']})"
        return r.get(f"{s}_note") or "não executado"
    md = md_table(["Grafo", "Vértices", "Arestas", "k", "Vetor (ms)", "Heap (ms)", "Speedup"],
                  [[r["graph"], f"{r['n']:,}".replace(",", "."), f"{r['m']:,}".replace(",", "."), r["k"],
                    cell(r, "vector"), cell(r, "heap"),
                    f"{r['speedup']:.0f}x ({r['paired_runs']} pares)" if r.get("speedup") else "-"]
                   for r in rows])
    md += ("\nEntre parênteses: execuções concluídas / k. Speedup = média vetor / média heap "
           "nas origens concluídas pelas duas estratégias.\n")
    with open(os.path.join(out, "summary.md"), "w", encoding="utf-8") as f:
        f.write(md)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    ap.add_argument("--graphs", nargs="*", default=WEIGHTED_GRAPHS)
    ap.add_argument("--k", type=int, default=100)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--strategies", nargs="*", default=["vector", "heap"], choices=sorted(QUEUES))
    ap.add_argument("--budget", type=float, default=1200,
                    help="max seconds of runs per (graph, strategy); 0 = unlimited")
    ap.add_argument("--run-timeout", type=float, default=900,
                    help="max seconds of a single run; 0 = unlimited")
    ap.add_argument("--representation", default="csr")
    ap.add_argument("--out", default=os.path.join(DEFAULT_RESULTS, "benchmarks"))
    ap.add_argument("--resume", action="store_true",
                    help="keep the runs already saved in <out>/<graph>.json and do only the missing ones")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for name in a.graphs:
        path = os.path.join(a.out, f"{name}.json")
        previous = read_json(path) if a.resume else None
        settings = {"k": a.k, "seed": a.seed, "budget_s": a.budget, "run_timeout_s": a.run_timeout,
                    "representation": a.representation}
        if previous and any(previous.get(key) != value for key, value in settings.items()
                            if key != "k") or (previous and previous["k"] != min(a.k, previous["n"])):
            raise SystemExit(f"{path} was made with other settings; run without --resume or use them: "
                             + str({key: previous.get(key) for key in settings}))
        done = {s: [r for r in previous["runs"] if r["strategy"] == s] for s in a.strategies} if previous \
            else {s: [] for s in a.strategies}
        if previous and all(len(done[s]) == previous["k"] for s in a.strategies):
            log(f"{name}: already complete, skipped")
            continue
        g, load_s, memory = load(a.data_dir, name, a.representation)
        sources = random.Random(a.seed).sample(range(1, g.n + 1), min(a.k, g.n))
        if previous and previous["sources"] != sources:
            raise SystemExit(f"{path}: the sources differ from the ones drawn now")
        data = previous or {"graph": name, "n": g.n, "m": g.m, "k": len(sources), "seed": a.seed,
                            "sources": sources, "budget_s": a.budget, "run_timeout_s": a.run_timeout,
                            "representation": a.representation, "load_s": load_s, "memory_mb": memory,
                            "environment": environment(), "runs": []}

        def save():
            data["runs"] = [r for s in a.strategies for r in done[s]]
            write_json(path, data)
            write_tables(a.out)

        for strategy in a.strategies:
            bench(g, name, strategy, sources, a.budget, a.run_timeout, done[strategy], save)
        del g
    log(f"done: {a.out}/summary.md")


if __name__ == "__main__":
    main()
