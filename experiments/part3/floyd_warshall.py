"""Case study 2 (Part 3): Floyd-Warshall distances between the vertices {10, 20, 30, 40, 50}.

Usage (from the repository root):
  python -m experiments.part3.floyd_warshall [--data-dir ../T3] [--graphs grafo_W_1 ...]
                                             [--vertices 10 20 30 40 50] [--undirected]
                                             [--timeout 3600] [--timeout-for grafo_W_2=SECONDS]
                                             [--fw-workers P] [--fw-engine python|numpy|numba]
                                             [--from-benchmark results/part3/benchmark]
                                             [--max-memory-gb 16] [--max-vertices 25000]
Floyd-Warshall computes all n^2 distances and keeps two (n+1) x (n+1) matrices
(12 bytes per cell). Before starting, the size is checked from the first line
of the file: a graph whose matrices exceed --max-memory-gb (or with more than
--max-vertices vertices) is not run, and the record says why. Otherwise the run
happens in a separate process with --timeout (or the per-graph value of
--timeout-for) and a memory cap; a run that times out reports the stage k it
reached. --fw-workers splits the rows of each stage among P processes
(FloydWarshall(workers=P); same matrices as the sequential run); default: one
per CPU. --fw-engine numpy|numba uses an optional accelerated row loop.
--from-benchmark DIR: when study 3 already ran complete Floyd-Warshall rounds of
a graph (they record these pairs), the matrix is taken from its first finished
round instead of running Floyd-Warshall again; the record names the round and
says whether every round gave the same pairs.
The 5 x 5 table respects the direction: D[i][j] and D[j][i] are both computed.
When Floyd-Warshall gives no matrix (not run, timeout or negative cycle), the
same 25 distances are also computed with Bellman-Ford (one run per column, to
each of the 5 vertices), and the table says which algorithm produced them.
Outputs: results/part3/floyd_warshall/<graph>.json, table.md
"""
import argparse
import os
import time

from graphs import BellmanFord, FloydWarshall

from ..common import environment, graph_results, log, md_table, write_json
from ..memprobe import run_worker
from .common import (DEFAULT_DATA_DIR, DEFAULT_RESULTS, FW_ENGINES, WORKER_GRACE_S, PART3_GRAPHS, benchmark_fw_runs, cycle_info,
                     default_workers, fmt, graph_path, header_n, jsonable, load, per_graph)


def bellman_ford_pairs(path, vertices, directed) -> dict:
    """D[i][j] for i, j in `vertices` by Bellman-Ford to each j (the fallback)."""
    g, _, _ = load(path, directed)
    t = time.perf_counter()
    rev = g.reversed()
    pairs = {str(i): {} for i in vertices}
    cycles = []
    for j in vertices:
        r = BellmanFord().to_target(g, j, rev)
        if r.negative_cycle:
            cycles.append(cycle_info(g, r.negative_cycle))
        for i in vertices:
            pairs[str(i)][str(j)] = {"distance": jsonable(r.distance_from(i)), "path": r.path_from(i),
                                     "exact": r.exact}
    return {"pairs": pairs, "seconds": time.perf_counter() - t, "negative_cycles": cycles[:1]}


def study(path, name, a) -> dict:
    n = header_n(path)
    need = FloydWarshall.memory_bytes(n)
    timeout = per_graph(a.timeout_for).get(name, a.timeout)
    rec = {"graph": name, "n": n, "vertices": a.vertices, "directed": not a.undirected,
           "matrix_gib": need / 2**30, "timeout_s": timeout, "fw_workers": a.fw_workers, "fw_engine": a.fw_engine,
           "environment": environment()}
    reused = from_benchmark(a, name)
    if reused:
        rec["fw"] = reused
        rec["fw_engine"], rec["fw_workers"] = reused.get("engine"), reused.get("workers")
        log(f"{name}: Floyd-Warshall taken from {reused['source']}")
    elif need > a.max_memory_gb * 2**30 or (a.max_vertices and n > a.max_vertices):
        rec["fw"] = {"status": f"não executado: n = {n} exige {need / 2**30:,.1f} GiB nas duas matrizes "
                               f"(limites: {a.max_memory_gb:g} GiB, {a.max_vertices} vértices)"}
        log(f"{name}: {rec['fw']['status']}")
    else:
        log(f"{name}: Floyd-Warshall in a worker (matrices {need / 2**30:.1f} GiB, timeout {timeout:.0f} s, "
            f"{a.fw_workers} processes)...")
        rec["fw"] = run_worker("experiments.part3.worker",
                               ["--graph", path, "--algorithm", "fw", "--directed", int(not a.undirected),
                                "--max-vertices", a.max_vertices, "--timeout", timeout,
                                "--workers", a.fw_workers, "--engine", a.fw_engine, "--pairs", *a.vertices],
                               timeout=timeout + WORKER_GRACE_S if timeout else None,
                               max_memory_gb=a.max_memory_gb + 2)
        log(f"{name}: Floyd-Warshall {rec['fw']['status']}"
            + (f" in {rec['fw']['seconds']:.1f} s" if rec["fw"].get("seconds") else ""))
    if "pairs" not in rec["fw"] and a.fallback:
        log(f"{name}: computing the same pairs with Bellman-Ford")
        rec["bellman_ford"] = bellman_ford_pairs(path, a.vertices, not a.undirected)
    return rec


def from_benchmark(a, name):
    """The first finished Floyd-Warshall round of study 3 with these pairs, or None."""
    found = benchmark_fw_runs(a.from_benchmark, name) if a.from_benchmark else None
    if not found:
        return None
    runs, settings = found
    want = [str(v) for v in a.vertices]
    for r in runs:
        if r.get("seconds") is None:
            continue
        if r.get("negative_cycle"):  # the round answered "negative cycle": no matrix to take
            rec = {**r, "status": "negative cycle"}
        elif r.get("pairs") and sorted(r["pairs"]) == sorted(want):
            rec = dict(r)
        else:
            continue
        others = [x["pairs"] for x in runs if x.get("pairs")]
        rec["source"] = f"estudo 3, rodada {r['round']} ({os.path.join(a.from_benchmark, name + '.json')})"
        rec["rounds_with_same_pairs"] = f"{sum(p == others[0] for p in others)}/{len(others)}" if others else None
        rec["benchmark_settings"] = settings
        return rec
    return None


def matrix_md(d) -> str:
    vs = d["vertices"]
    if "pairs" in d["fw"]:
        pairs, method = d["fw"]["pairs"], "Floyd-Warshall" + (
            f" ({d['fw']['source']}; pares iguais em {d['fw']['rounds_with_same_pairs']} rodadas)"
            if d["fw"].get("source") else "")
    elif "bellman_ford" in d:
        pairs = d["bellman_ford"]["pairs"]
        method = f"Bellman-Ford (Floyd-Warshall: {d['fw']['status']})"
    else:
        return f"**{d['graph']}**: Floyd-Warshall {d['fw']['status']}; sem matriz.\n"
    rows = [[f"**{i}**"] + [fmt(pairs[str(i)][str(j)]["distance"]) for j in vs] for i in vs]
    return (f"**{d['graph']}** — linha = origem, coluna = destino; calculado com {method}\n\n"
            + md_table(["de \\ para"] + [str(j) for j in vs], rows))


def write_tables(out):
    datas = graph_results(out)
    md = "\n".join(matrix_md(d) for d in datas)
    md += "\n" + md_table(
        ["Grafo", "n", "Matrizes (GiB)", "Floyd-Warshall", "Tempo FW (s)", "Etapa k alcançada", "Ciclo negativo"],
        [[d["graph"], d["n"], f"{d['matrix_gib']:.2f}", d["fw"]["status"],
          f"{d['fw']['seconds']:.1f}" if d["fw"].get("seconds") else "-", d["fw"].get("progress", "-"),
          f"sim ({d['fw']['negative_cycle']['edges']} arestas, etapa k = {d['fw']['stopped_at']})"
          if d["fw"].get("negative_cycle") else "-"] for d in datas])
    with open(os.path.join(out, "table.md"), "w", encoding="utf-8") as f:
        f.write(md)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    ap.add_argument("--graphs", nargs="*", default=PART3_GRAPHS)
    ap.add_argument("--vertices", type=int, nargs="*", default=[10, 20, 30, 40, 50])
    ap.add_argument("--undirected", action="store_true")
    ap.add_argument("--timeout", type=float, default=3600, help="seconds for the Floyd-Warshall call; 0 = none")
    ap.add_argument("--timeout-for", nargs="*", default=[], metavar="NAME=SECONDS",
                    help="per-graph timeout, e.g. grafo_W_2=90000")
    ap.add_argument("--fw-workers", type=int, default=default_workers(),
                    help="processes per Floyd-Warshall stage (1 = sequential)")
    ap.add_argument("--fw-engine", choices=FW_ENGINES, default="python",
                    help="Floyd-Warshall row loop: python (standard library), numpy or numba (optional)")
    ap.add_argument("--from-benchmark", default=None, metavar="DIR",
                    help="take the matrix from a finished Floyd-Warshall round of study 3 in DIR")
    ap.add_argument("--max-memory-gb", type=float, default=16, help="limit for the two matrices")
    ap.add_argument("--max-vertices", type=int, default=25000)
    ap.add_argument("--no-fallback", dest="fallback", action="store_false",
                    help="do not compute the pairs with Bellman-Ford when Floyd-Warshall gives no matrix")
    ap.add_argument("--out", default=os.path.join(DEFAULT_RESULTS, "floyd_warshall"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for name in a.graphs:
        path = graph_path(a.data_dir, name)
        name = os.path.splitext(os.path.basename(path))[0]
        write_json(os.path.join(a.out, f"{name}.json"), study(path, name, a))
        write_tables(a.out)
    log(f"done: {a.out}/table.md")


if __name__ == "__main__":
    main()
