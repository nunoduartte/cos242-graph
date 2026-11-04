"""Case study C: shortest paths from Edsger W. Dijkstra in the collaboration network.

Usage (from the repository root):
  python -m experiments.collaboration [--data-dir ../T2]
Names are matched exactly (UTF-8) against rede_colaboracao_vertices.txt, and a
single heap Dijkstra from the source answers every target.
Outputs: results/part2/collaboration/result.json, table.csv, table.md
"""
import argparse
import os
import time

from graphs import Dijkstra, IndexedMinHeap, VertexLabels

from .common import (DEFAULT_DATA_DIR, DEFAULT_RESULTS, environment, fmt_distance, load, log,
                     md_table, write_csv, write_json)

SOURCE = "Edsger W. Dijkstra"
TARGETS = ["Alan M. Turing", "J. B. Kruskal", "Jon M. Kleinberg", "Éva Tardos", "Daniel R. Figueiredo"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    ap.add_argument("--graph", default="rede_colaboracao")
    ap.add_argument("--names", default="rede_colaboracao_vertices.txt")
    ap.add_argument("--source", default=SOURCE)
    ap.add_argument("--targets", nargs="*", default=TARGETS)
    ap.add_argument("--representation", default="list")
    ap.add_argument("--out", default=os.path.join(DEFAULT_RESULTS, "collaboration"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    labels = VertexLabels.read(os.path.join(a.data_dir, a.names))
    g, load_s, memory = load(a.data_dir, a.graph, a.representation)
    source = labels.id_of(a.source)
    if source is None:
        raise SystemExit(f"source researcher {a.source!r} not found in {a.names}")
    t = time.perf_counter()
    result = Dijkstra(IndexedMinHeap).run(g, source)
    dijkstra_s = time.perf_counter() - t
    log(f"Dijkstra from {a.source} (vertex {source}) in {dijkstra_s:.2f} s")

    rows = []
    for name in a.targets:
        v = labels.id_of(name)
        path = result.path_to(v) if v is not None else None
        status = "not found" if v is None else ("ok" if path else "unreachable")
        rows.append({"source": a.source, "source_id": source, "target": name, "target_id": v,
                     "status": status, "distance": result.distance_to(v) if path else None,
                     "edges": len(path) - 1 if path else None,
                     "path_ids": path, "path_names": labels.names(path) if path else None})
        log(f"{name} ({v}): {status}" + (f", distance {fmt_distance(rows[-1]['distance'])}, "
                                         f"{rows[-1]['edges']} edges" if path else ""))

    write_json(os.path.join(a.out, "result.json"),
               {"source": a.source, "source_id": source, "n": g.n, "m": g.m, "load_s": load_s,
                "memory_mb": memory, "dijkstra_s": dijkstra_s,
                "reachable": sum(p >= 0 for p in result.parent), "rows": rows, "environment": environment()})
    write_csv(os.path.join(a.out, "table.csv"),
              [dict(r, path_ids=" ".join(map(str, r["path_ids"] or [])),
                    path_names=" | ".join(r["path_names"] or [])) for r in rows],
              ["source", "source_id", "target", "target_id", "status", "distance", "edges",
               "path_ids", "path_names"])
    labels_pt = {"not found": "pesquisador não encontrado", "unreachable": "inalcançável"}
    md = md_table(["Pesquisador de origem", "Pesquisador de destino", "Distância", "Arestas", "Caminho"],
                  [[r["source"], r["target"],
                    fmt_distance(r["distance"]) if r["status"] == "ok" else labels_pt[r["status"]],
                    r["edges"] if r["status"] == "ok" else "-",
                    " → ".join(r["path_names"]) if r["status"] == "ok" else "-"] for r in rows])
    with open(os.path.join(a.out, "table.md"), "w", encoding="utf-8") as f:
        f.write(md)
    log(f"done: {a.out}/table.md")


if __name__ == "__main__":
    main()
