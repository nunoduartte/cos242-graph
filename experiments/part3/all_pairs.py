"""Case study 4 (Part 3): all-pairs Bellman-Ford x Floyd-Warshall, mean of 10 rounds each.

Usage (from the repository root):
  python -m experiments.part3.all_pairs [--data-dir ../T3] [--graphs grafo_W_1 grafo_W_2]
                                        [--subgraphs grafo_W_2:500,1000,2000,3000,4000] [--rounds 10]
                                        [--run-timeout 1800] [--budget 7200] [--max-memory-gb 16] [--resume]
                                        [--timeout-for grafo_W_2=S] [--budget-for grafo_W_2=S] [--fw-workers P]
                                        [--fw-engine python|numpy|numba]
                                        [--fw-from-benchmark results/part3/benchmark]
Equal scope: both algorithms produce the same AllPairsShortestPaths, i.e. the n x n
distance matrix and the predecessor matrix (one tree of shortest paths per
vertex). Bellman-Ford does it with n runs of the same core used in study 1
(BellmanFord.all_pairs, one per source); both stop at the first negative cycle.
Every round runs in its own process (memory cap, clean heap); only the
algorithm call is timed. The first finished round of each algorithm also
writes a digest of its distance matrix, and the two digests are compared.

The official graphs are large for an O(n^3) algorithm in pure Python, so the
study also runs on subgraphs induced by the vertices 1..N of a graph
(--subgraphs NAME:N1,N2,...), written to <out>/subgraphs/; this shows how n and
m change the comparison. A round that times out reports how far it got
(stage k or sources done); the report derives from it an extrapolation of the
full time, always labelled as such: elapsed x n / progress for Bellman-Ford (the
sources cost about the same), and for Floyd-Warshall an upper bound, because
its stages do not: stage k only processes the rows i with D[i][k] finite, few
at the start (see experiments.part3.fw_calibrate for the exact count).
--timeout-for / --budget-for give a graph its own limits (both algorithms);
--fw-workers splits each Floyd-Warshall stage among P processes; --fw-engine
numpy|numba uses an optional accelerated row loop. --fw-from-benchmark DIR:
for a graph whose complete Floyd-Warshall rounds study 3 already measured (same
call, same scope: FloydWarshall.run), those rounds are used instead of being
run again; the record says so.
Outputs: results/part3/all_pairs/<graph>.json, summary.csv, summary.md
"""
import argparse
import os

from graphs import FloydWarshall

from ..common import environment, graph_results, log, md_table, read_json, write_csv, write_json
from ..memory_representations import induced_prefix
from ..memprobe import run_worker
from .common import (DEFAULT_DATA_DIR, DEFAULT_RESULTS, FW_ENGINES, WORKER_GRACE_S, benchmark_fw_runs, default_workers, graph_path,
                     header_n, per_graph, run_rounds, summarize_runs)

ALGORITHMS = {"bellman-ford": "bf-all", "floyd-warshall": "fw"}


def make_subgraphs(specs, data_dir, out) -> list:
    """NAME:N1,N2 -> paths of the induced subgraphs (created once, then reused)."""
    paths = []
    os.makedirs(os.path.join(out, "subgraphs"), exist_ok=True)
    for spec in specs:
        name, sizes = spec.split(":")
        src = graph_path(data_dir, name)
        base = os.path.splitext(os.path.basename(src))[0]
        for size in map(int, sizes.split(",")):
            dst = os.path.join(out, "subgraphs", f"{base}_1-{size}.txt")
            if not os.path.exists(dst):
                edges = induced_prefix(src, size, dst)
                log(f"{dst}: {edges} edges")
            paths.append(dst)
    return paths


def round_runner(path, alg, a, digest_done, run_timeout):
    n = header_n(path)
    need = FloydWarshall.memory_bytes(n)  # both algorithms return the same two matrices
    refusal = None
    if need > a.max_memory_gb * 2**30 or (a.max_vertices and n > a.max_vertices):
        refusal = (f"refused: n = {n} needs {need / 2**30:,.1f} GiB for the matrices "
                   f"(limits {a.max_memory_gb:g} GiB, {a.max_vertices} vertices)")

    def one(i, remaining):
        if refusal:
            return {"status": refusal, "seconds": None}
        limit = min(x for x in (run_timeout, remaining) if x) if (run_timeout or remaining) else 0
        rec = run_worker("experiments.part3.worker",
                         ["--graph", path, "--algorithm", ALGORITHMS[alg], "--directed", int(not a.undirected),
                          "--max-vertices", a.max_vertices, "--timeout", limit, "--workers", a.fw_workers,
                          "--engine", a.fw_engine,
                          "--digest", int(not digest_done())],
                         timeout=limit + WORKER_GRACE_S if limit else None, max_memory_gb=a.max_memory_gb + 2)
        if rec["status"] == "negative cycle":
            rec["status"] = "ok (negative cycle found)"
        return rec
    return one


def extrapolation(runs, n):
    """Full-run time from an interrupted round, an estimate and never a measurement.
    Bellman-Ford (no rows_done): elapsed x n / sources done. Floyd-Warshall: an
    upper bound, elapsed + (n - k) remaining stages x (n - 1) rows x (n + 1) cells
    x the cost per cell measured so far (the remaining stages have at most n - 1
    rows each; elapsed x n / k would be far too low, as the first stages are cheap)."""
    for r in runs:
        elapsed, k = r.get("interrupted_after_s"), r.get("progress")
        if not (elapsed and k):
            continue
        if r.get("rows_done") is None:
            return {"seconds": elapsed * n / k, "progress": k, "elapsed_s": elapsed, "kind": "proportional"}
        if not r["rows_done"]:
            return None
        per_cell = elapsed / (r["rows_done"] * (n + 1))
        return {"seconds": elapsed + (n - k + 1) * (n - 1) * (n + 1) * per_cell, "progress": k,
                "elapsed_s": elapsed, "kind": "upper bound", "per_cell_ns": per_cell * 1e9}
    return None


def write_tables(out):
    datas = graph_results(out)
    rows = []
    for d in datas:
        row = {"graph": d["graph"], "n": d["n"], "m": d.get("m"), "digests_equal": d.get("digests_equal")}
        for alg, runs in d["runs"].items():
            s = summarize_runs(runs)
            for k, v in s.items():
                row[f"{alg}_{k}"] = v
            ext = extrapolation(runs, d["n"])
            row[f"{alg}_extrapolated_s"] = ext["seconds"] if ext else None
            row[f"{alg}_extrapolation"] = ext
        bf, fw = row.get("bellman-ford_mean_s"), row.get("floyd-warshall_mean_s")
        row["fw_over_bf"] = fw / bf if bf and fw else None
        rows.append(row)
    cols = ["graph", "n", "m", "digests_equal"] + [f"{a}_{k}" for a in ALGORITHMS for k in
                                                   ("rounds", "finished", "mean_s", "stdev_s", "outcome", "note",
                                                    "extrapolated_s")] + ["fw_over_bf"]
    write_csv(os.path.join(out, "summary.csv"), rows, cols)

    def cell(r, alg):
        if r.get(f"{alg}_mean_s") is not None:
            sd = r.get(f"{alg}_stdev_s")
            return (f"{r[f'{alg}_mean_s']:.4f}" + (f" ± {sd:.4f}" if sd is not None else "")
                    + f" ({r[f'{alg}_finished']}/{r[f'{alg}_rounds']})")
        note = r.get(f"{alg}_note") or "não executado"
        ext = r.get(f"{alg}_extrapolated_s")
        if not ext:
            return note
        word = "limite superior estimado" if ext["kind"] == "upper bound" else "extrapolação"
        return note + f"; {word} ≈ {ext['seconds'] / 3600:,.1f} h"
    md = md_table(["Grafo", "n", "m", "Bellman-Ford, todos os pares (s)", "Floyd-Warshall (s)", "FW / BF",
                   "Mesmas distâncias"],
                  [[r["graph"], r["n"], r["m"] or "-", cell(r, "bellman-ford"), cell(r, "floyd-warshall"),
                    f"{r['fw_over_bf']:.2f}" if r["fw_over_bf"] else "-",
                    {True: "sim", False: "NÃO"}.get(r["digests_equal"], "-")] for r in rows])
    md += ("\nMédia ± desvio-padrão amostral das rodadas concluídas (concluídas/rodadas). Mesmo escopo: matriz "
           "n x n de distâncias e de predecessores. Estimativas, não medições: extrapolação (Bellman-Ford) = "
           "tempo até a interrupção x n / origens concluídas; limite superior (Floyd-Warshall) = tempo até a "
           "interrupção + etapas restantes x (n - 1) linhas x (n + 1) células x custo por célula medido.\n")
    with open(os.path.join(out, "summary.md"), "w", encoding="utf-8") as f:
        f.write(md)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    ap.add_argument("--graphs", nargs="*", default=["grafo_W_1", "grafo_W_2"])
    ap.add_argument("--subgraphs", nargs="*", default=["grafo_W_2:500,1000,2000,3000,4000"],
                    help="NAME:N1,N2,... induced subgraphs on vertices 1..N")
    ap.add_argument("--algorithms", nargs="*", default=list(ALGORITHMS), choices=list(ALGORITHMS))
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--undirected", action="store_true")
    ap.add_argument("--run-timeout", type=float, default=1800, help="seconds per round; 0 = none")
    ap.add_argument("--budget", type=float, default=7200, help="seconds per (graph, algorithm); 0 = none")
    ap.add_argument("--max-memory-gb", type=float, default=16)
    ap.add_argument("--max-vertices", type=int, default=25000)
    ap.add_argument("--timeout-for", nargs="*", default=[], metavar="NAME=SECONDS",
                    help="per-graph round timeout (both algorithms), e.g. grafo_W_2=90000")
    ap.add_argument("--budget-for", nargs="*", default=[], metavar="NAME=SECONDS",
                    help="per-graph budget (each algorithm), e.g. grafo_W_2=900000")
    ap.add_argument("--fw-workers", type=int, default=default_workers(),
                    help="processes per Floyd-Warshall stage (1 = sequential)")
    ap.add_argument("--fw-engine", choices=FW_ENGINES, default="python",
                    help="Floyd-Warshall row loop: python (standard library), numpy or numba (optional)")
    ap.add_argument("--fw-from-benchmark", default=None, metavar="DIR",
                    help="use the Floyd-Warshall rounds study 3 measured in DIR for the graphs it has")
    ap.add_argument("--out", default=os.path.join(DEFAULT_RESULTS, "all_pairs"))
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    paths = make_subgraphs(a.subgraphs, a.data_dir, a.out) + [graph_path(a.data_dir, g) for g in a.graphs]
    timeouts, budgets = per_graph(a.timeout_for), per_graph(a.budget_for)
    for path in paths:
        name = os.path.splitext(os.path.basename(path))[0]
        run_timeout, budget = timeouts.get(name, a.run_timeout), budgets.get(name, a.budget)
        settings = {"rounds": a.rounds, "directed": not a.undirected, "run_timeout_s": run_timeout,
                    "budget_s": budget, "fw_workers": a.fw_workers, "fw_engine": a.fw_engine}
        out_path = os.path.join(a.out, f"{name}.json")
        data = read_json(out_path) if a.resume else None
        if data and any(data["settings"].get(k) != v for k, v in settings.items()):
            raise SystemExit(f"{out_path} was made with other settings {data['settings']}; run without --resume")
        data = data or {"graph": name, "n": header_n(path), "m": None, "settings": settings,
                        "environment": environment(), "runs": {}}

        def save():
            digests = {alg: next((r["digest"] for r in runs if r.get("digest")), None)
                       for alg, runs in data["runs"].items()}
            if len(digests) == 2 and all(digests.values()):
                data["digests_equal"] = len(set(digests.values())) == 1
            data["m"] = data["m"] or next((r["m"] for runs in data["runs"].values() for r in runs if r.get("m")),
                                          None)
            write_json(out_path, data)
            write_tables(a.out)

        for alg in a.algorithms:
            runs = data["runs"].setdefault(alg, [])
            reused = benchmark_fw_runs(a.fw_from_benchmark, name) if (
                a.fw_from_benchmark and alg == "floyd-warshall") else None
            if reused:
                src = os.path.join(a.fw_from_benchmark, f"{name}.json")
                runs[:] = [{**r, "source": f"estudo 3 ({src})"} for r in reused[0][:a.rounds]]
                data["fw_from_benchmark"] = {"source": src, "settings": reused[1]}
                save()
                log(f"{name} {alg}: {len(runs)} rounds taken from {src}")
                continue
            digest_done = lambda runs=runs: any(r.get("digest") for r in runs)
            run_rounds(runs, a.rounds, budget, round_runner(path, alg, a, digest_done, run_timeout), save,
                       f"{name} {alg}")
    log(f"done: {a.out}/summary.md")


if __name__ == "__main__":
    main()
