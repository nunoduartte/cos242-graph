"""Case study A: distance and shortest path from vertex 10 to 20, 30, 40, 50, 60.

Usage (from the repository root):
  python -m experiments.shortest_paths [--data-dir ../T2] [--graphs grafo_W_3 ...]
                                       [--validate-timeout 600]
One Dijkstra (heap) per graph answers the five targets. Two independent checks:
  - optimality certificate, O(m), always: no edge can shorten a distance
    (dist[v] <= dist[u] + w) and every parent edge is tight (dist[v] = dist[p] + w);
  - the vector version from the same source, every distance compared, when it
    finishes within --validate-timeout seconds (0 skips it).
Outputs: results/part2/shortest_paths/<graph>.json, table.csv, table.md
"""
import argparse
import math
import os
import time

from graphs import Dijkstra, IndexedMinHeap, VectorQueue

from .common import (DEFAULT_DATA_DIR, DEFAULT_RESULTS, WEIGHTED_GRAPHS, RunTimeout, environment,
                     fmt_distance, graph_results, load, log, md_table, time_limit, write_csv, write_json)

TOLERANCE = 1e-9


def compare(a, b) -> float:
    """Largest difference between two distance vectors (inf if reachability differs)."""
    worst = 0.0
    for x, y in zip(a, b):
        if x != y:
            if math.isinf(x) or math.isinf(y):
                return math.inf
            worst = max(worst, abs(x - y) / max(1.0, abs(x)))
    return worst


def certificate(g, result) -> dict:
    """Checks the optimality conditions of a shortest-path tree on every edge."""
    dist, parent, s = result.distance, result.parent, result.source
    edges = violations = 0
    for u in g.vertices():
        du = dist[u]
        for v, w in g.weighted_neighbors(u):
            edges += 1
            d = du + w
            if d - dist[v] < -TOLERANCE * max(1.0, d):  # also catches a reachable v left at inf
                violations += 1
        p = parent[u]
        if u != s and p > 0 and abs(dist[p] + g.weight(p, u) - du) > TOLERANCE * max(1.0, du):
            violations += 1
        if (p >= 0) != (du < math.inf):
            violations += 1
    return {"status": "ok" if violations == 0 and dist[s] == 0 else "FAILED",
            "violations": violations, "edge_entries_checked": edges}


def study(g, name, source, targets, validate_timeout):
    t = time.perf_counter()
    result = Dijkstra(IndexedMinHeap).run(g, source)
    heap_s = time.perf_counter() - t
    rows = []
    for v in targets:
        path = result.path_to(v)
        rows.append({"graph": name, "source": source, "target": v,
                     "distance": result.distance_to(v) if path else None,
                     "edges": len(path) - 1 if path else None, "path": path})
        log(f"{name}: d({source},{v}) = {fmt_distance(result.distance_to(v))}, "
            f"{len(path) - 1 if path else '-'} edges")
    t = time.perf_counter()
    cert = certificate(g, result)
    cert["seconds"] = time.perf_counter() - t
    log(f"{name}: optimality certificate: {cert['status']} ({cert['edge_entries_checked']} edge entries)")
    validation = {"status": "skipped"}
    if validate_timeout:
        try:
            t = time.perf_counter()
            with time_limit(validate_timeout):
                other = Dijkstra(VectorQueue).run(g, source)
            diff = compare(result.distance, other.distance)
            validation = {"status": "equal" if diff <= TOLERANCE else "DIFFERENT",
                          "max_relative_difference": diff, "vector_s": time.perf_counter() - t,
                          "vertices_compared": g.n}
        except RunTimeout:
            validation = {"status": f"vector not finished in {validate_timeout} s"}
        log(f"{name}: vector vs heap: {validation['status']}")
    return {"graph": name, "n": g.n, "m": g.m, "source": source, "heap_s": heap_s,
            "reachable": sum(p >= 0 for p in result.parent), "rows": rows, "certificate": cert,
            "validation": validation}


def write_tables(out):
    rows, checks = [], []
    for data in graph_results(out):
        rows += data["rows"]
        cert = data.get("certificate", {}).get("status", "not run")
        checks.append([data["graph"], cert, data["validation"]["status"]])
    write_csv(os.path.join(out, "table.csv"),
              [dict(r, path=" ".join(map(str, r["path"])) if r["path"] else "no path") for r in rows],
              ["graph", "source", "target", "distance", "edges", "path"])
    md = md_table(["Grafo", "Origem", "Destino", "Distância", "Arestas", "Caminho"],
                  [[r["graph"], r["source"], r["target"],
                    fmt_distance(r["distance"]) if r["path"] else "sem caminho",
                    r["edges"] if r["path"] else "-",
                    " → ".join(map(str, r["path"])) if r["path"] else "inalcançável"] for r in rows])
    md += ("\nValidação: certificado de otimalidade em todas as arestas e comparação de todas as "
           "distâncias com o Dijkstra com vetor (quando terminou dentro do limite):\n\n")
    md += md_table(["Grafo", "Certificado", "Vetor x heap"], checks)
    with open(os.path.join(out, "table.md"), "w", encoding="utf-8") as f:
        f.write(md)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    ap.add_argument("--graphs", nargs="*", default=WEIGHTED_GRAPHS)
    ap.add_argument("--source", type=int, default=10)
    ap.add_argument("--targets", nargs="*", type=int, default=[20, 30, 40, 50, 60])
    ap.add_argument("--validate-timeout", type=float, default=600,
                    help="seconds allowed for the vector run that cross-checks the heap (0 = skip)")
    ap.add_argument("--representation", default="csr")
    ap.add_argument("--out", default=os.path.join(DEFAULT_RESULTS, "shortest_paths"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for name in a.graphs:
        g, load_s, memory = load(a.data_dir, name, a.representation)
        data = study(g, name, a.source, a.targets, a.validate_timeout)
        data.update(load_s=load_s, memory_mb=memory, representation=a.representation,
                    environment=environment())
        write_json(os.path.join(a.out, f"{name}.json"), data)
        write_tables(a.out)  # after every graph, so finished graphs are never lost
        del g
    log(f"done: {a.out}/table.md")


if __name__ == "__main__":
    main()
