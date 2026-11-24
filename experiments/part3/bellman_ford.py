"""Case study 1 (Part 3): Bellman-Ford distances from 10, 20 and 30 to vertex 100.

Usage (from the repository root):
  python -m experiments.part3.bellman_ford [--data-dir ../T3] [--graphs grafo_W_1 ...] [--target 100]
                                           [--sources 10 20 30] [--undirected] [--timeout 1800]
The target is common, so one run per graph answers every source: Bellman-Ford
to a target computes the distance of all vertices to it at once. The graphs are
read as directed (each line "u v w" is the edge u -> v) unless --undirected.
Each graph also gets:
  - a search for any negative cycle in the whole graph (not only the ones that
    reach the target), as the assignment asks whether the graph has one;
  - a validation when there is no negative cycle: the optimality certificate on
    every edge (dist[u] <= w(u, v) + dist[v], and the successor edge is tight)
    and, when no weight is negative, the comparison with Dijkstra on G^T.
Outputs: results/part3/bellman_ford/<graph>.json, table.csv, table.md
"""
import argparse
import gc
import os
import time

from graphs import BellmanFord, Dijkstra

from ..common import RunTimeout, environment, graph_results, log, md_table, time_limit, write_csv, write_json
from .common import (DEFAULT_DATA_DIR, DEFAULT_RESULTS, INF, PART3_GRAPHS, cycle_info, fmt, graph_path,
                     jsonable, load)

TOLERANCE = 1e-9


def certificate(g, r) -> dict:
    """Optimality conditions of a tree of shortest paths to the target, on every edge."""
    dist, succ, t = r.distance, r.successor, r.target
    edges = violations = 0
    for u in g.vertices():
        du = dist[u]
        for v, w in g.weighted_neighbors(u):
            edges += 1
            if dist[v] != INF and du - (w + dist[v]) > TOLERANCE * max(1.0, abs(du)):
                violations += 1
        s = succ[u]
        if u != t and s > 0 and abs(g.weight(u, s) + dist[s] - du) > TOLERANCE * max(1.0, abs(du)):
            violations += 1
        if (s >= 0) != (du < INF):
            violations += 1
    return {"status": "ok" if violations == 0 and dist[t] == 0 else "FAILED",
            "violations": violations, "edges_checked": edges}


def compare_with_dijkstra(rev, r) -> dict:
    t = time.perf_counter()
    d = Dijkstra().run(rev, r.target).distance
    diff = max((abs(a - b) if a != b else 0.0) for a, b in zip(d[1:], r.distance[1:]))
    return {"status": "ok" if diff <= 1e-9 else "FAILED", "max_difference": diff,
            "seconds": time.perf_counter() - t}


def study(path, name, a) -> dict:
    g, load_s, memory = load(path, not a.undirected, a.representation)
    rec = {"graph": name, "n": g.n, "m": g.m, "directed": g.directed, "min_weight": g.min_weight,
           "negative_edges": None, "target": a.target, "load_s": load_s, "memory_mb": memory,
           "environment": environment(), "sources": []}
    rec["negative_edges"] = sum(1 for u in g.vertices() for _, w in g.weighted_neighbors(u) if w < 0)
    bf = BellmanFord()
    gc.collect()
    gc.disable()
    t0 = time.perf_counter()
    try:
        with time_limit(a.timeout or None):
            rev = g.reversed()
            t1 = time.perf_counter()
            r = bf.to_target(g, a.target, rev)
        t2 = time.perf_counter()
    except RunTimeout:
        rec["status"] = f"timeout (> {a.timeout:.0f} s)"
        log(f"{name}: {rec['status']}")
        return rec
    finally:
        gc.enable()
    rec.update(status="ok", reverse_s=t1 - t0, solve_s=t2 - t1, seconds=t2 - t0, passes=r.passes,
               relaxations=r.relaxations, exact=r.exact,
               negative_cycle_to_target=cycle_info(g, r.negative_cycle),
               vertices_minus_inf=sum(1 for d in r.distance[1:] if d == -INF),
               vertices_unreachable=sum(1 for d in r.distance[1:] if d == INF))
    log(f"{name}: Bellman-Ford to {a.target} in {rec['seconds']:.2f} s ({r.passes} passes, "
        f"{r.relaxations} relaxations), negative cycle to the target: {r.negative_cycle is not None}")
    for s in a.sources:
        d = r.distance_from(s)
        path = r.path_from(s)
        if d == -INF:
            status = "ciclo negativo no caminho (distância −∞)"
        elif d == INF:
            status = "inalcançável"
        elif not r.exact:
            status = "não confirmado (há ciclo negativo; valor é só limite superior)"
        else:
            status = "ok"
        rec["sources"].append({"source": s, "distance": jsonable(d), "edges": len(path) - 1 if path else None,
                               "path": path, "status": status})
    if a.global_check:
        t = time.perf_counter()
        cycle = bf.find_negative_cycle(g)
        rec["negative_cycle_in_graph"] = cycle_info(g, cycle)
        rec["global_check_s"] = time.perf_counter() - t
        log(f"{name}: graph has a negative cycle: {cycle is not None}")
    if r.exact and a.validate:
        rec["certificate"] = certificate(g, r)
        if g.min_weight >= 0:
            rec["dijkstra"] = compare_with_dijkstra(rev, r)
        log(f"{name}: validation {rec['certificate']['status']}"
            + (f", Dijkstra {rec['dijkstra']['status']}" if "dijkstra" in rec else ""))
    return rec


def write_tables(out):
    datas = graph_results(out)
    rows = [{"graph": d["graph"], "target": d["target"], **s} for d in datas for s in d.get("sources", [])]
    write_csv(os.path.join(out, "table.csv"), [{**r, "path": " ".join(map(str, r["path"] or []))} for r in rows],
              ["graph", "source", "target", "distance", "edges", "status", "path"])
    md = md_table(["Grafo", "Origem", "Destino", "Distância", "Arestas", "Status", "Caminho"],
                  [[r["graph"], r["source"], r["target"], fmt(r["distance"]), r["edges"] or "-", r["status"],
                    " → ".join(map(str, r["path"])) if r["path"] else "-"] for r in rows])
    md += "\n" + md_table(
        ["Grafo", "n", "m", "Arestas negativas", "Ciclo negativo até o destino", "Ciclo negativo no grafo",
         "Rodadas", "Relaxamentos", "Tempo (s)", "Validação"],
        [[d["graph"], d["n"], d["m"], d.get("negative_edges"),
          _cycle_cell(d.get("negative_cycle_to_target")) if d.get("status") == "ok" else d.get("status"),
          _cycle_cell(d.get("negative_cycle_in_graph")) if "negative_cycle_in_graph" in d else "não verificado",
          d.get("passes", "-"), d.get("relaxations", "-"),
          f"{d['seconds']:.2f}" if d.get("seconds") is not None else "-", _validation_cell(d)] for d in datas])
    with open(os.path.join(out, "table.md"), "w", encoding="utf-8") as f:
        f.write(md)


def _cycle_cell(c):
    return f"sim ({c['edges']} arestas, peso {fmt(c['weight'])})" if c else "não"


def _validation_cell(d):
    parts = []
    if "certificate" in d:
        parts.append(f"certificado {d['certificate']['status']}")
    if "dijkstra" in d:
        parts.append(f"Dijkstra {d['dijkstra']['status']}")
    return ", ".join(parts) or "-"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    ap.add_argument("--graphs", nargs="*", default=PART3_GRAPHS)
    ap.add_argument("--target", type=int, default=100)
    ap.add_argument("--sources", type=int, nargs="*", default=[10, 20, 30])
    ap.add_argument("--undirected", action="store_true", help="read the graphs as undirected")
    ap.add_argument("--representation", default="csr")
    ap.add_argument("--timeout", type=float, default=1800, help="seconds for the Bellman-Ford call; 0 = none")
    ap.add_argument("--no-global-check", dest="global_check", action="store_false",
                    help="skip the search for a negative cycle anywhere in the graph")
    ap.add_argument("--no-validate", dest="validate", action="store_false")
    ap.add_argument("--out", default=os.path.join(DEFAULT_RESULTS, "bellman_ford"))
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
