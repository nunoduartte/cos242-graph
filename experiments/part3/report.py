"""Collects the four Part 3 case studies into results/part3/report/.

Usage (from the repository root):  python -m experiments.part3.report
Reads only what the studies wrote (nothing is recomputed or estimated here)
and lists every study that is still missing.
Outputs: results.md, all_pairs.svg (time x n of study 4), status.json
"""
import argparse
import math
import os
from html import escape

from ..common import environment, graph_results, write_json
from ..tables import BLUE, GRID, INK, MUTED, ORANGE, br
from .all_pairs import extrapolation
from .common import DEFAULT_RESULTS, summarize_runs

STUDIES = [("bellman_ford", "table.md", "1. Bellman-Ford: distância de 10, 20 e 30 até 100"),
           ("floyd_warshall", "table.md", "2. Floyd-Warshall: distâncias entre {10, 20, 30, 40, 50}"),
           ("benchmark", "summary.md", "3. Tempo médio em 10 rodadas"),
           ("all_pairs", "summary.md", "4. Bellman-Ford para todos os pares x Floyd-Warshall")]


def read_text(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()


def all_pairs_points(results):
    """(n, m, algorithm, mean seconds) of every finished all-pairs measurement."""
    out = os.path.join(results, "all_pairs")
    if not os.path.isdir(out):
        return []
    points = []
    for d in graph_results(out):
        for alg, runs in d["runs"].items():
            s = summarize_runs(runs)
            if s["mean_s"]:
                points.append((d["n"], d.get("m"), alg, s["mean_s"], d["graph"]))
    return points


def all_pairs_svg(points) -> str:
    """Mean time against n, log-log, one line per algorithm (finished rounds only)."""
    if len({p[0] for p in points}) < 2:
        return ""
    width, height, left, top, bottom, right = 760, 400, 80, 70, 340, 40
    xs, ys = [p[0] for p in points], [p[3] for p in points]
    x_lo, x_hi = 10 ** math.floor(math.log10(min(xs))), 10 ** math.ceil(math.log10(max(xs)))
    y_lo, y_hi = 10 ** math.floor(math.log10(min(ys))), 10 ** math.ceil(math.log10(max(ys)))
    x = lambda v: left + (math.log10(v) - math.log10(x_lo)) / (math.log10(x_hi) - math.log10(x_lo)) * (
        width - left - right)
    y = lambda v: bottom - (math.log10(v) - math.log10(y_lo)) / (math.log10(y_hi) - math.log10(y_lo)) * (
        bottom - top)
    out = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {width} {height}' font-family='sans-serif' "
           f"font-size='12'><rect width='100%' height='100%' fill='white'/>",
           f"<text x='{left}' y='22' font-size='15' fill='{INK}'>Todos os pares: tempo médio por rodada "
           f"(s) x vértices (escala log-log)</text>"]
    for i, (alg, color, label) in enumerate((("bellman-ford", BLUE, "Bellman-Ford, n execuções"),
                                             ("floyd-warshall", ORANGE, "Floyd-Warshall"))):
        out.append(f"<rect x='{left + i * 220}' y='36' width='12' height='12' rx='2' fill='{color}'/>"
                   f"<text x='{left + i * 220 + 17}' y='46' fill='{INK}'>{label}</text>")
    t = y_lo
    while t <= y_hi:
        out.append(f"<line x1='{left}' x2='{width - right}' y1='{y(t):.1f}' y2='{y(t):.1f}' stroke='{GRID}'/>"
                   f"<text x='{left - 6}' y='{y(t) + 4:.1f}' text-anchor='end' fill='{MUTED}'>"
                   f"{br(t, 3) if t < 1 else br(t)}</text>")
        t *= 10
    t = x_lo
    while t <= x_hi:
        out.append(f"<text x='{x(t):.1f}' y='{bottom + 18}' text-anchor='middle' fill='{MUTED}'>{br(t)}</text>")
        t *= 10
    for alg, color in (("bellman-ford", BLUE), ("floyd-warshall", ORANGE)):
        pts = sorted((p for p in points if p[2] == alg), key=lambda p: p[0])
        if len(pts) > 1:
            out.append(f"<polyline fill='none' stroke='{color}' stroke-width='2' points='"
                       + " ".join(f"{x(p[0]):.1f},{y(p[3]):.1f}" for p in pts) + "'/>")
        for p in pts:
            out.append(f"<circle cx='{x(p[0]):.1f}' cy='{y(p[3]):.1f}' r='4' fill='{color}' stroke='white' "
                       f"stroke-width='2'><title>{escape(p[4])} (n = {p[0]}, m = {p[1]}): {br(p[3], 3)} s"
                       f"</title></circle>")
    out.append(f"<line x1='{left}' x2='{width - right}' y1='{bottom}' y2='{bottom}' stroke='#999'/>"
               f"<text x='{(left + width - right) / 2}' y='{bottom + 36}' text-anchor='middle' fill='{INK}'>"
               f"vértices (n)</text><text x='{left}' y='{height - 8}' fill='{MUTED}' font-size='11'>"
               f"Só rodadas concluídas (medidas). Mesmo escopo: as duas matrizes n x n.</text></svg>")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", default=DEFAULT_RESULTS)
    a = ap.parse_args()
    out = os.path.join(a.results, "report")
    os.makedirs(out, exist_ok=True)
    parts = ["# Parte 3 — resultados consolidados\n",
             "Gerado a partir de `results/part3/`; nada foi recalculado. Distâncias com duas casas "
             "(os pesos têm duas). −∞: o vértice alcança um ciclo negativo que alcança o destino.\n"]
    status = {}
    for folder, table, title in STUDIES:
        text = read_text(os.path.join(a.results, folder, table))
        status[folder] = "ok" if text else "pendente"
        parts.append(f"\n## {title}\n\n" + (text or "*Pendente: o estudo ainda não foi executado.*\n"))
    svg = all_pairs_svg(all_pairs_points(a.results))
    if svg:
        with open(os.path.join(out, "all_pairs.svg"), "w", encoding="utf-8") as f:
            f.write(svg)
        parts.append("\n![Todos os pares: tempo x n](all_pairs.svg)\n")
    ap_dir = os.path.join(a.results, "all_pairs")
    if os.path.isdir(ap_dir):
        ext = [(d["graph"], alg, extrapolation(runs, d["n"])) for d in graph_results(ap_dir)
               for alg, runs in d["runs"].items()]
        ext = [e for e in ext if e[2]]
        if ext:
            parts.append("\n### Extrapolações (não são medições)\n\n" + "".join(
                f"- {g}, {alg}: interrompido após {br(e['elapsed_s'], 0)} s com progresso {e['progress']}; "
                + ("limite superior estimado" if e.get("kind") == "upper bound" else "tempo total estimado")
                + f" ≈ {br(e['seconds'] / 3600, 1)} h\n" for g, alg, e in ext))
    with open(os.path.join(out, "results.md"), "w", encoding="utf-8") as f:
        f.write("".join(parts))
    write_json(os.path.join(out, "status.json"), {"studies": status, "environment": environment()})
    print(f"{out}/results.md: " + ", ".join(f"{k} {v}" for k, v in status.items()))


if __name__ == "__main__":
    main()
