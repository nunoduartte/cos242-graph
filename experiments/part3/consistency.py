"""Consistency checks across the four Part 3 studies (run after them).

Usage (from the repository root):
  python -m experiments.part3.consistency [--data-dir ../T3] [--no-recompute]
Reads results/part3/ and checks, writing results/part3/consistency.{json,md}:
  1. study 3: means use only finished rounds, and finished/rounds is what the table says;
  2. study 3: every complete Floyd-Warshall round of a graph gave the same 25 pairs
     and, when two digests exist, the same matrix;
  3. study 2 = study 3: the 5 x 5 matrix of study 2 is the one of a study 3 round;
  4. study 2 x Bellman-Ford: unless --no-recompute, the same 25 distances are
     computed again with Bellman-Ford to each of the 5 vertices (a different
     algorithm) and compared with the Floyd-Warshall matrix (tolerance 1e-9);
  5. study 1 x Floyd-Warshall: d(10|20|30 -> 100) is not in the 5 x 5 table, so
     the check is the negative cycle: in a graph where study 1 found one, study 3's
     Floyd-Warshall must also stop at one (and vice versa);
  6. study 4: the digests of the two algorithms are equal wherever both finished;
     the Floyd-Warshall rounds reused from study 3 are the same records.
Also: the all-pairs Bellman-Ford digest of an official graph = the Floyd-Warshall digest of study 3.
Nothing here is timed; it only reads results (and, for 4, runs Bellman-Ford;
--recompute-graphs restricts that to some graphs).
"""
import argparse
import json
import math
import os
import statistics

from ..common import log, md_table, write_json
from .common import DEFAULT_DATA_DIR, DEFAULT_RESULTS, from_json, graph_path

TOL = 1e-9


def read(path):
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def check_benchmark(res, checks):
    bench = os.path.join(res, "benchmark")
    for name in sorted(os.listdir(bench)) if os.path.isdir(bench) else []:
        if not name.endswith(".json"):
            continue
        d = read(os.path.join(bench, name))
        for alg, runs in d["runs"].items():
            finished = [r for r in runs if r.get("seconds") is not None]
            bad = [r["round"] for r in finished if not str(r["status"]).startswith("ok")]
            checks.append({"check": "3: média só com rodadas concluídas", "graph": d["graph"], "algorithm": alg,
                           "ok": not bad, "detail": f"{len(finished)}/{len(runs)} concluídas"
                           + (f"; status inesperado nas rodadas {bad}" if bad else "")})
        fw = [r for r in d["runs"].get("floyd-warshall", []) if r.get("pairs")]
        if len(fw) > 1:
            same = all(r["pairs"] == fw[0]["pairs"] for r in fw)
            checks.append({"check": "3: pares iguais em todas as rodadas do Floyd-Warshall", "graph": d["graph"],
                           "ok": same, "detail": f"{len(fw)} rodadas"})
        digests = {r["digest"] for r in d["runs"].get("floyd-warshall", []) if r.get("digest")}
        if len(digests) > 1:
            checks.append({"check": "3: digests iguais", "graph": d["graph"], "ok": False, "detail": str(digests)})


def check_study2(res, data_dir, recompute, checks, only=None):
    out = os.path.join(res, "floyd_warshall")
    for name in sorted(os.listdir(out)) if os.path.isdir(out) else []:
        if not name.endswith(".json"):
            continue
        d = read(os.path.join(out, name))
        fw = d["fw"]
        if "pairs" not in fw:
            continue
        bench = read(os.path.join(res, "benchmark", name))
        if bench:
            rounds = [r for r in bench["runs"].get("floyd-warshall", []) if r.get("pairs")]
            ok = any(r["pairs"] == fw["pairs"] for r in rounds)
            checks.append({"check": "2 = 3: matriz 5 x 5 vem de uma rodada do estudo 3", "graph": d["graph"],
                           "ok": ok, "detail": fw.get("source", "executado no estudo 2")})
        if recompute and (not only or d["graph"] in only):
            from graphs import BellmanFord
            from .common import load
            g, _, _ = load(graph_path(data_dir, d["graph"]), d.get("directed", True))
            rev = g.reversed()
            worst, paths_ok = 0.0, True
            for j in d["vertices"]:
                r = BellmanFord().to_target(g, j, rev)
                for i in d["vertices"]:
                    a, b = from_json(fw["pairs"][str(i)][str(j)]["distance"]), r.distance_from(i)
                    diff = 0.0 if a == b else abs(a - b)
                    worst = max(worst, diff if math.isfinite(diff) else math.inf)
                    p = fw["pairs"][str(i)][str(j)]["path"]
                    if p and abs(sum(g.weight(u, v) for u, v in zip(p, p[1:])) - a) > 1e-6:
                        paths_ok = False
            checks.append({"check": "2 x Bellman-Ford: as 25 distâncias recalculadas com Bellman-Ford",
                           "graph": d["graph"], "ok": worst <= TOL,
                           "detail": f"maior diferença {worst:.2e}"})
            checks.append({"check": "2: peso de cada caminho do Floyd-Warshall = distância", "graph": d["graph"],
                           "ok": paths_ok, "detail": "25 caminhos"})


def check_cycles(res, checks):
    s1 = os.path.join(res, "bellman_ford")
    for name in sorted(os.listdir(s1)) if os.path.isdir(s1) else []:
        if not name.endswith(".json"):
            continue
        d = read(os.path.join(s1, name))
        bench = read(os.path.join(res, "benchmark", name))
        fw = [r for r in (bench or {}).get("runs", {}).get("floyd-warshall", []) if r.get("seconds") is not None]
        if not fw:
            continue
        bf_cycle = d.get("negative_cycle_in_graph") is not None
        fw_cycle = all(r.get("negative_cycle") for r in fw)
        checks.append({"check": "1 x 3: ciclo negativo no Bellman-Ford ⇔ no Floyd-Warshall", "graph": d["graph"],
                       "ok": bf_cycle == fw_cycle,
                       "detail": f"Bellman-Ford: {'sim' if bf_cycle else 'não'}; "
                                 f"Floyd-Warshall: {'sim' if fw_cycle else 'não'} ({len(fw)} rodadas)"})


def check_all_pairs(res, checks):
    for sub in ("all_pairs", "all_pairs_numba"):
        out = os.path.join(res, sub)
        for name in sorted(os.listdir(out)) if os.path.isdir(out) else []:
            if not name.endswith(".json"):
                continue
            d = read(os.path.join(out, name))
            if d.get("digests_equal") is not None:
                checks.append({"check": f"4: mesma matriz nos dois algoritmos ({sub})", "graph": d["graph"],
                               "ok": d["digests_equal"], "detail": "digest SHA-1 das distâncias"})
            if d.get("fw_from_benchmark"):
                bench = read(os.path.join(res, "benchmark", name))
                same = bench and [r.get("seconds") for r in bench["runs"]["floyd-warshall"]][:len(
                    d["runs"]["floyd-warshall"])] == [r.get("seconds") for r in d["runs"]["floyd-warshall"]]
                checks.append({"check": "4 = 3: rodadas do Floyd-Warshall reaproveitadas", "graph": d["graph"],
                               "ok": bool(same), "detail": d["fw_from_benchmark"]["source"]})
            bench = read(os.path.join(res, "benchmark", name))
            bf = next((r["digest"] for r in d["runs"].get("bellman-ford", []) if r.get("digest")), None)
            fw = next((r["digest"] for r in (bench or {}).get("runs", {}).get("floyd-warshall", [])
                       if r.get("digest")), None)
            if sub == "all_pairs" and bf and fw:
                checks.append({"check": "4 x 3: Bellman-Ford todos os pares = Floyd-Warshall do estudo 3",
                               "graph": d["graph"], "ok": bf == fw, "detail": "digest SHA-1 das distâncias"})
    # Floyd-Warshall python x numba on the same subgraphs
    for name in sorted(os.listdir(os.path.join(res, "all_pairs_numba"))) if os.path.isdir(
            os.path.join(res, "all_pairs_numba")) else []:
        if not name.endswith(".json"):
            continue
        a, b = read(os.path.join(res, "all_pairs", name)), read(os.path.join(res, "all_pairs_numba", name))
        if not (a and b):
            continue
        da = next((r["digest"] for r in a["runs"].get("floyd-warshall", []) if r.get("digest")), None)
        db = next((r["digest"] for r in b["runs"].get("floyd-warshall", []) if r.get("digest")), None)
        if da and db:
            checks.append({"check": "4: Floyd-Warshall python = numba (mesma matriz)", "graph": a["graph"],
                           "ok": da == db, "detail": "digest SHA-1 das distâncias"})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    ap.add_argument("--results", default=DEFAULT_RESULTS)
    ap.add_argument("--no-recompute", dest="recompute", action="store_false")
    ap.add_argument("--recompute-graphs", nargs="*", default=None,
                    help="recompute with Bellman-Ford only these graphs (default: all)")
    a = ap.parse_args()
    checks = []
    check_benchmark(a.results, checks)
    check_study2(a.results, a.data_dir, a.recompute, checks, a.recompute_graphs)
    check_cycles(a.results, checks)
    check_all_pairs(a.results, checks)
    write_json(os.path.join(a.results, "consistency.json"), {"checks": checks,
                                                            "all_ok": all(c["ok"] for c in checks)})
    md = md_table(["Verificação", "Grafo", "Resultado", "Detalhe"],
                  [[c["check"] + (f" ({c['algorithm']})" if c.get("algorithm") else ""), c["graph"],
                    "ok" if c["ok"] else "FALHOU", c["detail"]] for c in checks])
    with open(os.path.join(a.results, "consistency.md"), "w", encoding="utf-8") as f:
        f.write(md + f"\n{sum(c['ok'] for c in checks)}/{len(checks)} verificações ok.\n")
    log(f"{sum(c['ok'] for c in checks)}/{len(checks)} checks ok: {a.results}/consistency.md")


if __name__ == "__main__":
    main()
