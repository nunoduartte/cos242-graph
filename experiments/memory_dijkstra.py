"""Memory of Dijkstra: extra RSS of the vector and heap strategies over the loaded graph.

Usage (from the repository root):
  python -m experiments.memory_dijkstra [--data-dir ../T2] [--graphs grafo_W_3] [--source 10]
                                        [--strategies vector heap] [--timeout 900] [--max-memory-gb 20]
                                        [--tracemalloc]
Each (graph, strategy) runs in its own Python process, as in Part 1, so no
allocation of an earlier run is counted. The worker records:
  - baseline RSS (interpreter + modules), RSS after loading the graph, and the
    graph's share (the difference), as the Part 1 memory column;
  - for the Dijkstra call alone: RSS before, peak RSS (kernel high-water mark,
    reset right before the call; see experiments/memprobe.py) and the increase;
  - the time of the call (perf_counter, garbage collector paused, as in the
    benchmark) and its status. A run stopped by --timeout still reports the
    peak reached until then, marked as partial.
--tracemalloc also reports the peak of Python allocations made by the call
(exact bytes of the algorithm's objects), but makes the run several times
slower, so its time is flagged and must not be compared with the benchmark.
This is separate from the official time benchmark (experiments.benchmark).
Outputs: results/part2/memory_dijkstra/runs.json, runs.csv, table.md
"""
import argparse
import gc
import os
import time

from .common import (DEFAULT_DATA_DIR, DEFAULT_RESULTS, RunTimeout, environment, log, md_table,
                     read_json, time_limit, write_csv, write_json)
from .memprobe import clean_baseline, emit, peak_rss, rss_mb, run_worker

COLUMNS = ["graph", "n", "m", "strategy", "source", "representation", "status", "baseline_rss_mb",
           "rss_after_load_mb", "graph_mb", "load_s", "rss_before_mb", "peak_rss_mb", "peak_increase_mb",
           "rss_after_mb", "peak_method", "dijkstra_s", "reachable", "tracemalloc_peak_mb", "process_s"]


def worker(a):
    from graphs import Dijkstra, GraphReader
    from graphs.priority_queues import QUEUES
    rec = {"graph": a.graph, "strategy": a.strategy, "source": a.source, "representation": a.representation,
           "baseline_rss_mb": clean_baseline()}
    t = time.perf_counter()
    g = GraphReader.read(a.file, a.representation)
    rec.update(load_s=time.perf_counter() - t, n=g.n, m=g.m)
    gc.collect()
    rec["rss_after_load_mb"] = rss_mb()
    rec["graph_mb"] = rec["rss_after_load_mb"] - rec["baseline_rss_mb"]
    dijkstra = Dijkstra(QUEUES[a.strategy])
    if a.tracemalloc:
        import tracemalloc
        tracemalloc.start()
    result = None
    with peak_rss(rec):
        gc.disable()
        t = time.perf_counter()
        try:
            with time_limit(a.timeout):
                result = dijkstra.run(g, a.source)
            rec["status"] = "ok"
            rec["dijkstra_s"] = time.perf_counter() - t
        except RunTimeout:
            rec["status"] = f"timeout (> {a.timeout:.0f} s): partial peak"
            rec["interrupted_after_s"] = time.perf_counter() - t
        except MemoryError:
            rec["status"] = "memory error (--max-memory-gb): partial peak"
        finally:
            gc.enable()
    if a.tracemalloc:
        rec["tracemalloc_peak_mb"] = tracemalloc.get_traced_memory()[1] / 2**20
        tracemalloc.stop()
        rec["note"] = "run under tracemalloc: dijkstra_s is inflated, not comparable"
    if result is not None:
        rec["reachable"] = sum(p >= 0 for p in result.parent)
    emit(rec)


def write_tables(out, rows):
    write_csv(os.path.join(out, "runs.csv"), rows, COLUMNS)

    def mb(x):
        return "-" if x is None else f"{x:,.0f}".replace(",", ".")
    md = md_table(["Grafo", "Estratégia", "Grafo carregado (MB)", "RSS antes (MB)", "Pico RSS (MB)",
                   "Aumento observado (MB)", "Tempo (s)", "Status"],
                  [[r["graph"], r["strategy"], mb(r.get("graph_mb")), mb(r.get("rss_before_mb")),
                    mb(r.get("peak_rss_mb")), mb(r.get("peak_increase_mb")),
                    f"{r['dijkstra_s']:.2f}" if r.get("dijkstra_s") is not None else "-", r["status"]]
                   for r in rows])
    md += ("\nAumento observado = pico de RSS durante a chamada de Dijkstra menos o RSS imediatamente antes "
           "(grafo já carregado). É uma aproximação da memória adicional do algoritmo: inclui o resultado "
           "(distâncias e pais) e o que o alocador do Python reteve, e não é o tamanho exato das estruturas.\n")
    with open(os.path.join(out, "table.md"), "w", encoding="utf-8") as f:
        f.write(md)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--file", help=argparse.SUPPRESS)
    ap.add_argument("--graph", help=argparse.SUPPRESS)
    ap.add_argument("--strategy", help=argparse.SUPPRESS)
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    ap.add_argument("--graphs", nargs="*", default=["grafo_W_3"])
    ap.add_argument("--strategies", nargs="*", default=["vector", "heap"])
    ap.add_argument("--source", type=int, default=10)
    ap.add_argument("--representation", default="csr")
    ap.add_argument("--timeout", type=float, default=900, help="max seconds of the Dijkstra call")
    ap.add_argument("--load-timeout", type=float, default=1800,
                    help="extra seconds allowed for the worker to start and load the graph")
    ap.add_argument("--max-memory-gb", type=float, default=20,
                    help="address-space limit of each worker (0 = none)")
    ap.add_argument("--tracemalloc", action="store_true")
    ap.add_argument("--out", default=os.path.join(DEFAULT_RESULTS, "memory_dijkstra"))
    a = ap.parse_args()
    if a.worker:
        return worker(a)

    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, "runs.json")
    data = read_json(path, {"runs": []})
    data["environment"] = environment()
    for name in a.graphs:
        for strategy in a.strategies:
            log(f"{name} {strategy}: worker started (source {a.source})")
            args = ["--file", os.path.join(a.data_dir, f"{name}.txt"), "--graph", name, "--strategy", strategy,
                    "--source", a.source, "--representation", a.representation, "--timeout", a.timeout]
            if a.tracemalloc:
                args.append("--tracemalloc")
            rec = run_worker("experiments.memory_dijkstra", args, a.timeout + a.load_timeout, a.max_memory_gb)
            rec.setdefault("graph", name)
            rec.setdefault("strategy", strategy)
            rec.setdefault("source", a.source)
            rec["settings"] = {"timeout_s": a.timeout, "max_memory_gb": a.max_memory_gb,
                               "tracemalloc": a.tracemalloc}
            # a new measurement of the same (graph, strategy, source) replaces the old one
            data["runs"] = [r for r in data["runs"] if (r["graph"], r["strategy"], r["source"], bool(
                r.get("tracemalloc_peak_mb") is not None)) != (name, strategy, a.source, a.tracemalloc)]
            data["runs"].append(rec)
            write_json(path, data)
            write_tables(a.out, data["runs"])
            log(f"{name} {strategy}: {rec['status']}, peak +{rec.get('peak_increase_mb', float('nan')):.0f} MB")
    log(f"done: {a.out}/table.md")


if __name__ == "__main__":
    main()
