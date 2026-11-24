"""Case study 3 (Part 3): mean time of Bellman-Ford and of Floyd-Warshall over 10 rounds.

Usage (from the repository root):
  python -m experiments.part3.benchmark [--data-dir ../T3] [--graphs grafo_W_1 ...] [--rounds 10]
                                        [--algorithms bellman-ford floyd-warshall] [--target 100]
                                        [--run-timeout 1800] [--budget 7200] [--max-memory-gb 16] [--resume]
                                        [--fw-timeout-for grafo_W_2=S] [--fw-budget-for grafo_W_2=S]
                                        [--fw-workers P] [--fw-engine python|numpy|numba]
                                        [--fw-pairs 10 20 30 40 50]
Scope of each timed call (reading and writing files are never timed):
  bellman-ford    the computation of study 1: distances and tree of shortest
                  paths from every vertex to --target, i.e. building G^T
                  (Graph.reversed) plus BellmanFord.to_target. Both parts are
                  also recorded separately. The graph is loaded once per graph.
  floyd-warshall  the computation of study 2: FloydWarshall.run, all n^2
                  distances and the predecessor matrix. Each round runs in its
                  own process (memory cap, clean heap); loading is not timed.
                  --fw-workers P splits the rows of each stage among P
                  processes (same matrices as the sequential run);
                  --fw-engine numpy|numba runs the same row loop with an
                  optional accelerated engine (graphs/floyd_warshall_engines.py).
                  After the timed call (not timed) each round also extracts
                  D[i][j] for --fw-pairs (the 5 x 5 table of study 2) and the
                  first finished round a digest of the whole distance matrix
                  (study 4); so one complete run serves studies 2, 3 and 4:
                  run study 2 with --from-benchmark and study 4 with
                  --fw-from-benchmark.
These two scopes are different (one target vs. all pairs); study 4 compares
equal scopes. A round stopped by a negative cycle is a finished round (the
algorithm answered "negative cycle") and is labelled as such.
Limits: --run-timeout per round, --budget per (graph, algorithm); after a
timeout or a refused run (graph above the Floyd-Warshall size limits) the next
rounds are recorded as "not run". --fw-timeout-for and --fw-budget-for give a
graph its own Floyd-Warshall limits (e.g. a longer one for grafo_W_2). Every round is saved when it ends; --resume
continues an interrupted benchmark without repeating rounds.
Outputs: results/part3/benchmark/<graph>.json, runs.csv, summary.csv, summary.md
"""
import argparse
import gc
import os
import time

from graphs import BellmanFord, FloydWarshall

from ..common import RunTimeout, environment, graph_results, log, md_table, read_json, time_limit, write_csv, \
    write_json
from ..memprobe import run_worker
from .common import (DEFAULT_DATA_DIR, DEFAULT_RESULTS, FW_ENGINES, WORKER_GRACE_S, PART3_GRAPHS, default_workers, graph_path,
                     header_n, load, per_graph, run_rounds, summarize_runs)

ALGORITHMS = ["bellman-ford", "floyd-warshall"]


def bellman_ford_round(g, target, run_timeout):
    def one(i, remaining):
        limit = min(x for x in (run_timeout, remaining) if x) if (run_timeout or remaining) else None
        gc.collect()
        gc.disable()
        t0 = time.perf_counter()
        try:
            with time_limit(limit):
                rev = g.reversed()
                t1 = time.perf_counter()
                r = BellmanFord().to_target(g, target, rev)
            t2 = time.perf_counter()
        except RunTimeout:
            return {"status": f"timeout (> {limit:.0f} s)", "seconds": None,
                    "interrupted_after_s": time.perf_counter() - t0}
        finally:
            gc.enable()
        return {"status": "ok" if r.exact else "ok (negative cycle found)", "seconds": t2 - t0,
                "reverse_s": t1 - t0, "solve_s": t2 - t1, "passes": r.passes, "relaxations": r.relaxations}
    return one


def floyd_warshall_round(path, a, run_timeout, runs):
    n = header_n(path)
    need = FloydWarshall.memory_bytes(n)
    refusal = None
    if need > a.max_memory_gb * 2**30 or (a.max_vertices and n > a.max_vertices):
        refusal = (f"refused: n = {n} needs {need / 2**30:,.1f} GiB for the matrices "
                   f"(limits {a.max_memory_gb:g} GiB, {a.max_vertices} vertices)")

    def one(i, remaining):
        if refusal:
            return {"status": refusal, "seconds": None}
        limit = min(x for x in (run_timeout, remaining) if x) if (run_timeout or remaining) else 0
        rec = run_worker("experiments.part3.worker",
                         ["--graph", path, "--algorithm", "fw", "--directed", int(not a.undirected),
                          "--max-vertices", a.max_vertices, "--timeout", limit, "--workers", a.fw_workers,
                          "--engine", a.fw_engine, "--digest", int(not any(r.get("digest") for r in runs)),
                          "--pairs", *a.fw_pairs],
                         timeout=limit + WORKER_GRACE_S if limit else None, max_memory_gb=a.max_memory_gb + 2)
        if rec["status"] == "negative cycle":
            rec["status"] = "ok (negative cycle found)"
        return rec
    return one


def write_tables(out):
    datas = graph_results(out)
    write_csv(os.path.join(out, "runs.csv"),
              [{"graph": d["graph"], "algorithm": alg, **r} for d in datas for alg, runs in d["runs"].items()
               for r in runs],
              ["graph", "algorithm", "round", "status", "seconds", "reverse_s", "solve_s", "passes",
               "interrupted_after_s", "progress", "rows_done", "workers", "engine", "peak_increase_mb"])
    rows = []
    for d in datas:
        for alg, runs in d["runs"].items():
            rows.append({"graph": d["graph"], "n": d["n"], "m": d.get("m"), "algorithm": alg,
                         **summarize_runs(runs)})
    write_csv(os.path.join(out, "summary.csv"), rows,
              ["graph", "n", "m", "algorithm", "rounds", "finished", "mean_s", "stdev_s", "min_s", "max_s",
               "outcome", "note"])

    def cell(r):
        if r["mean_s"] is None:
            return r["note"] or "não executado"
        sd = f" ± {r['stdev_s']:.4f}" if r["stdev_s"] is not None else ""
        return f"{r['mean_s']:.4f}{sd} ({r['finished']}/{r['rounds']})"
    by = {}
    for r in rows:
        by.setdefault(r["graph"], {})[r["algorithm"]] = r
    md = md_table(["Grafo", "n", "m", "Bellman-Ford até o destino (s)", "Floyd-Warshall (s)"],
                  [[g, v[next(iter(v))]["n"], v[next(iter(v))]["m"] or "-",
                    cell(v["bellman-ford"]) if "bellman-ford" in v else "-",
                    cell(v["floyd-warshall"]) if "floyd-warshall" in v else "-"] for g, v in by.items()])
    for d in datas:
        fw_pairs = [r["pairs"] for r in d["runs"].get("floyd-warshall", []) if r.get("pairs")]
        if len(fw_pairs) > 1:
            same = all(p == fw_pairs[0] for p in fw_pairs)
            md += (f"\n{d['graph']}: distâncias e caminhos do estudo 2 iguais nas {len(fw_pairs)} rodadas do "
                   f"Floyd-Warshall: {'sim' if same else 'NÃO'}\n")
    md += ("\nMédia ± desvio-padrão amostral das rodadas concluídas (concluídas/rodadas). "
           "Escopos diferentes: Bellman-Ford calcula as distâncias de todos os vértices até um destino; "
           "Floyd-Warshall, todos os pares.\n")
    with open(os.path.join(out, "summary.md"), "w", encoding="utf-8") as f:
        f.write(md)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    ap.add_argument("--graphs", nargs="*", default=PART3_GRAPHS)
    ap.add_argument("--algorithms", nargs="*", default=ALGORITHMS, choices=ALGORITHMS)
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--target", type=int, default=100)
    ap.add_argument("--undirected", action="store_true")
    ap.add_argument("--run-timeout", type=float, default=1800, help="seconds per round; 0 = none")
    ap.add_argument("--budget", type=float, default=7200, help="seconds per (graph, algorithm); 0 = none")
    ap.add_argument("--max-memory-gb", type=float, default=16, help="Floyd-Warshall matrices limit")
    ap.add_argument("--max-vertices", type=int, default=25000, help="Floyd-Warshall vertex limit")
    ap.add_argument("--fw-timeout-for", nargs="*", default=[], metavar="NAME=SECONDS",
                    help="per-graph Floyd-Warshall round timeout, e.g. grafo_W_2=90000")
    ap.add_argument("--fw-budget-for", nargs="*", default=[], metavar="NAME=SECONDS",
                    help="per-graph Floyd-Warshall budget, e.g. grafo_W_2=900000")
    ap.add_argument("--fw-workers", type=int, default=default_workers(),
                    help="processes per Floyd-Warshall stage (1 = sequential)")
    ap.add_argument("--fw-engine", choices=FW_ENGINES, default="python",
                    help="Floyd-Warshall row loop: python (standard library), numpy or numba (optional)")
    ap.add_argument("--fw-pairs", type=int, nargs="*", default=[10, 20, 30, 40, 50],
                    help="vertices whose D[i][j] each Floyd-Warshall round records (study 2)")
    ap.add_argument("--out", default=os.path.join(DEFAULT_RESULTS, "benchmark"))
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    fw_timeouts, fw_budgets = per_graph(a.fw_timeout_for), per_graph(a.fw_budget_for)
    for name in a.graphs:
        path = graph_path(a.data_dir, name)
        name = os.path.splitext(os.path.basename(path))[0]
        fw_timeout, fw_budget = fw_timeouts.get(name, a.run_timeout), fw_budgets.get(name, a.budget)
        settings = {"rounds": a.rounds, "target": a.target, "directed": not a.undirected,
                    "run_timeout_s": a.run_timeout, "budget_s": a.budget, "fw_workers": a.fw_workers,
                    "fw_engine": a.fw_engine}
        if name in fw_timeouts or name in fw_budgets:
            settings.update(fw_run_timeout_s=fw_timeout, fw_budget_s=fw_budget)
        out_path = os.path.join(a.out, f"{name}.json")
        data = read_json(out_path) if a.resume else None
        if data and any(data["settings"].get(k) != v for k, v in settings.items()):
            raise SystemExit(f"{out_path} was made with other settings {data['settings']}; run without --resume")
        data = data or {"graph": name, "n": header_n(path), "m": None, "settings": settings,
                        "environment": environment(), "runs": {}}

        def save():
            write_json(out_path, data)
            write_tables(a.out)

        for alg in a.algorithms:
            runs = data["runs"].setdefault(alg, [])
            if len(runs) >= a.rounds:
                log(f"{name} {alg}: already complete")
                continue
            if alg == "bellman-ford":
                g, load_s, _ = load(path, not a.undirected)
                data.update(m=g.m, load_s=load_s)
                run_rounds(runs, a.rounds, a.budget, bellman_ford_round(g, a.target, a.run_timeout), save,
                           f"{name} {alg}")
                del g
            else:
                run_rounds(runs, a.rounds, fw_budget, floyd_warshall_round(path, a, fw_timeout, runs), save,
                           f"{name} {alg}")
    log(f"done: {a.out}/summary.md")


if __name__ == "__main__":
    main()
