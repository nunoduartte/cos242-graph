"""Memory and load time of the three representations: list, matrix and CSR.

Usage (from the repository root):
  python -m experiments.memory_representations [--data-dir ../T2] [--base grafo_W_3]
         [--sizes 2000 5000 10000 20000] [--full grafo_W_3] [--representations list matrix csr]
         [--matrix-max-gb 4] [--timeout 1800]
Subgraphs: the subgraph of size N is the subgraph of --base induced by the
vertices 1..N (every edge with both ends <= N, weights kept). It is
deterministic (no sampling), reproducible from the official file, and in the
weighted graphs provided the vertex numbers carry no structure, so 1..N is an
arbitrary vertex sample of the same random graph. The files are written once to
<out>/subgraphs/ and reused.
--full loads whole official graphs as well (matrix is skipped automatically:
the weighted matrix takes 9 (n+1)^2 bytes, above --matrix-max-gb it is not built).
Each (graph, representation) runs in its own Python process; the worker
records the RSS before loading, the RSS after loading (graph = difference, the
Part 1 memory column), the peak RSS during reading + construction (kernel
high-water mark, see experiments/memprobe.py) and the load time.
Outputs: results/part2/representations/runs.json, runs.csv, table.md
"""
import argparse
import gc
import os
import time

from .common import (DEFAULT_DATA_DIR, DEFAULT_RESULTS, environment, log, md_table, read_json,
                     write_csv, write_json)
from .memprobe import clean_baseline, emit, peak_rss, rss_mb, run_worker

COLUMNS = ["graph", "kind", "n", "m", "representation", "status", "load_s", "baseline_rss_mb",
           "rss_after_mb", "graph_mb", "peak_rss_mb", "peak_increase_mb", "peak_method", "process_s"]


def induced_prefix(src: str, size: int, dst: str) -> int:
    """Writes the subgraph of src induced by vertices 1..size; returns its edge lines."""
    edges = 0
    tmp = dst + ".part"
    with open(src) as f, open(tmp, "w") as out:
        n = int(f.readline())
        if size > n:
            raise ValueError(f"{src} has only {n} vertices, cannot take {size}")
        out.write(f"{size}\n")
        for line in f:
            parts = line.split()
            if len(parts) >= 2 and int(parts[0]) <= size and int(parts[1]) <= size:
                out.write(line if line.endswith("\n") else line + "\n")
                edges += 1
    os.replace(tmp, dst)  # only complete files get the final name
    return edges


def matrix_bytes(n: int) -> int:
    """Weighted matrix: one byte of presence + 8 of weight per cell."""
    return 9 * (n + 1) ** 2


def worker(a):
    from graphs import GraphReader
    rec = {"graph": a.graph, "representation": a.representation, "baseline_rss_mb": clean_baseline()}
    t = time.perf_counter()
    with peak_rss(rec):
        try:
            g = GraphReader.read(a.file, a.representation)
            rec["status"] = "ok"
        except MemoryError:
            g = None
            rec["status"] = "memory error (--max-memory-gb): partial peak"
    rec["load_s"] = time.perf_counter() - t
    if g is not None:
        gc.collect()
        rec.update(n=g.n, m=g.m, rss_after_mb=rss_mb())
        rec["graph_mb"] = rec["rss_after_mb"] - rec["baseline_rss_mb"]
    rec.pop("rss_before_mb", None)  # same as the baseline here
    emit(rec)


def write_tables(out, rows):
    write_csv(os.path.join(out, "runs.csv"), rows, COLUMNS)

    def num(x, fmt="{:,.0f}"):
        return "-" if x is None else fmt.format(x).replace(",", ".")
    md = md_table(["Grafo/subgrafo", "Vértices", "Arestas", "Representação", "Tempo de carga (s)",
                   "Memória (MB)", "Pico na construção (MB)", "Status"],
                  [[r["graph"], num(r.get("n")), num(r.get("m")), r["representation"],
                    num(r.get("load_s"), "{:.2f}") if r["status"] == "ok" else "-", num(r.get("graph_mb")),
                    num(r.get("peak_increase_mb")), r["status"]] for r in rows])
    md += ("\nMemória = RSS após a carga menos o RSS do processo antes da carga (mesma medida da Parte 1). "
           "Pico na construção = maior RSS durante leitura + construção menos o mesmo ponto de partida; "
           "inclui buffers temporários (por exemplo, a lista de arestas antes da CSR).\n")
    with open(os.path.join(out, "table.md"), "w", encoding="utf-8") as f:
        f.write(md)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--file", help=argparse.SUPPRESS)
    ap.add_argument("--graph", help=argparse.SUPPRESS)
    ap.add_argument("--representation", help=argparse.SUPPRESS)
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    ap.add_argument("--base", default="grafo_W_3", help="official graph the subgraphs come from")
    ap.add_argument("--sizes", nargs="*", type=int, default=[2000, 5000, 10000, 20000])
    ap.add_argument("--full", nargs="*", default=["grafo_W_3"], help="official graphs loaded whole")
    ap.add_argument("--representations", nargs="*", default=["list", "matrix", "csr"])
    ap.add_argument("--matrix-max-gb", type=float, default=4)
    ap.add_argument("--timeout", type=float, default=1800, help="max seconds of each worker")
    ap.add_argument("--max-memory-gb", type=float, default=20,
                    help="address-space limit of each worker (0 = none)")
    ap.add_argument("--out", default=os.path.join(DEFAULT_RESULTS, "representations"))
    a = ap.parse_args()
    if a.worker:
        return worker(a)

    os.makedirs(os.path.join(a.out, "subgraphs"), exist_ok=True)
    path = os.path.join(a.out, "runs.json")
    data = read_json(path, {"runs": []})
    data.update(environment=environment(), selection={
        "base": a.base, "sizes": a.sizes, "rule": "subgraph induced by vertices 1..N, weights kept"})
    inputs = []
    for size in a.sizes:
        name = f"{a.base}_1-{size}"
        file = os.path.join(a.out, "subgraphs", f"{name}.txt")
        if not os.path.exists(file):
            m = induced_prefix(os.path.join(a.data_dir, f"{a.base}.txt"), size, file)
            log(f"{name}: {m} edge lines written")
        inputs.append((name, "subgraph", file, size))
    for name in a.full:
        file = os.path.join(a.data_dir, f"{name}.txt")
        with open(file) as f:
            inputs.append((name, "official", file, int(f.readline())))

    for name, kind, file, n in inputs:
        for rep in a.representations:
            if rep == "matrix" and matrix_bytes(n) > a.matrix_max_gb * 2**30:
                rec = {"graph": name, "kind": kind, "n": n, "representation": rep,
                       "status": f"not built: needs ~{matrix_bytes(n) / 2**30:.1f} GiB > --matrix-max-gb"}
            else:
                log(f"{name} {rep}: worker started")
                rec = run_worker("experiments.memory_representations",
                                 ["--file", file, "--graph", name, "--representation", rep],
                                 a.timeout, a.max_memory_gb)
                rec.update(graph=name, kind=kind, representation=rep)
                rec.setdefault("n", n)
            data["runs"] = [r for r in data["runs"] if (r["graph"], r["representation"]) != (name, rep)]
            data["runs"].append(rec)
            write_json(path, data)
            write_tables(a.out, data["runs"])
            log(f"{name} {rep}: {rec['status']}")
    log(f"done: {a.out}/table.md")


if __name__ == "__main__":
    main()
