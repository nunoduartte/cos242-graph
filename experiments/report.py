"""Collects the results of the three case studies into results/part2/report/.

Usage (from the repository root):  python -m experiments.report
Reads only what the studies wrote (nothing is recomputed or estimated) and
lists every study or measurement that is still missing.
Outputs: results.md (studies A-C and Tables A-D), benchmark.svg, representations.svg,
construction_peak.svg, status.json
"""
import argparse
import math
import os
from html import escape

from .common import DEFAULT_RESULTS, environment, graph_results, read_json, write_json


def read_text(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()


def benchmark_svg(rows) -> str:
    """Grouped bars (log scale) of the mean time per run, in seconds; a run that hit
    the time limit is drawn as an open dashed bar up to that limit, labelled '>'."""
    from .tables import BLUE, GRID, INK, MUTED, ORANGE, br
    width, height, left, y0, bottom = 760, 380, 70, 80, 320
    vals = []
    for r in rows:
        for s in ("vector", "heap"):
            v = r.get(f"{s}_mean_ms") or r.get(f"{s}_limit_ms")
            if v:
                vals.append(v / 1000)
    if not vals:
        return ""
    lo = 10 ** math.floor(math.log10(min(vals)))
    hi = 10 ** math.ceil(math.log10(max(vals)))
    y = lambda v: bottom - (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * (bottom - y0)
    band = (width - left - 20) / len(rows)
    bar = band / 4
    out = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {width} {height}' font-family='sans-serif' "
           f"font-size='12'><rect width='100%' height='100%' fill='white'/>",
           f"<text x='{left}' y='22' font-size='15' fill='{INK}'>Tempo médio de Dijkstra por origem "
           f"(s, escala log)</text>",
           f"<rect x='{left}' y='34' width='12' height='12' rx='2' fill='{ORANGE}'/>"
           f"<text x='{left + 17}' y='44' fill='{INK}'>vetor, O(n² + m)</text>",
           f"<rect x='{left + 150}' y='34' width='12' height='12' rx='2' fill='{BLUE}'/>"
           f"<text x='{left + 167}' y='44' fill='{INK}'>heap, O((n + m) log n)</text>"]
    t = lo
    while t <= hi:
        out.append(f"<line x1='{left}' x2='{width - 20}' y1='{y(t):.1f}' y2='{y(t):.1f}' stroke='{GRID}'/>"
                   f"<text x='{left - 6}' y='{y(t) + 4:.1f}' text-anchor='end' fill='{MUTED}'>{br(t)}</text>")
        t *= 10
    for i, r in enumerate(rows):
        x = left + i * band + band / 2 - bar
        for j, (s, color) in enumerate((("vector", ORANGE), ("heap", BLUE))):
            bx = x + j * bar
            v, limit = r.get(f"{s}_mean_ms"), r.get(f"{s}_limit_ms")
            if v:
                v /= 1000
                out.append(f"<path d='M{bx:.1f},{bottom} V{y(v) + 4:.1f} q0,-4 4,-4 H{bx + bar - 6:.1f} "
                           f"q4,0 4,4 V{bottom} Z' fill='{color}'><title>{escape(r['graph'])} {s}: "
                           f"{br(v, 2)} s (média de {r[f'{s}_runs']} execuções)</title></path>"
                           f"<text x='{bx + bar / 2 - 1:.1f}' y='{y(v) - 5:.1f}' text-anchor='middle' "
                           f"font-size='11' fill='{INK}'>{br(v, 1 if v < 100 else 0)}</text>")
            elif limit:
                limit /= 1000
                out.append(f"<rect x='{bx:.1f}' y='{y(limit):.1f}' width='{bar - 2:.1f}' "
                           f"height='{bottom - y(limit):.1f}' fill='none' stroke='{color}' stroke-width='1.5' "
                           f"stroke-dasharray='4 3'><title>{escape(r['graph'])} {s}: não terminou em "
                           f"{limit:.0f} s</title></rect>"
                           f"<text x='{bx + bar / 2 - 1:.1f}' y='{y(limit) - 5:.1f}' text-anchor='middle' "
                           f"font-size='11' fill='{INK}'>&gt; {limit:.0f}</text>")
        out.append(f"<text x='{left + i * band + band / 2:.1f}' y='{bottom + 18}' text-anchor='middle' "
                   f"fill='{INK}'>{escape(r['graph'])}</text>")
    out.append(f"<line x1='{left}' x2='{width - 20}' y1='{bottom}' y2='{bottom}' stroke='#999'/>"
               f"<text x='{left}' y='{height - 14}' fill='{MUTED}' font-size='11'>Barras tracejadas: o vetor não "
               f"terminou nenhuma execução dentro do limite indicado (limite medido, não estimativa).</text>"
               "</svg>")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", default=DEFAULT_RESULTS)
    a = ap.parse_args()
    out = os.path.join(a.results, "report")
    os.makedirs(out, exist_ok=True)
    status, parts = {}, ["# Resultados da Parte 2 (gerado por `python -m experiments.report`)\n"]

    for key, title, path in [
            ("shortest_paths", "Estudo A: caminhos mínimos a partir do vértice 10", "shortest_paths/table.md"),
            ("benchmark", "Estudo B: tempo médio de Dijkstra, vetor x heap", "benchmarks/summary.md"),
            ("collaboration", "Estudo C: rede de colaboração a partir de Edsger W. Dijkstra",
             "collaboration/table.md")]:
        text = read_text(os.path.join(a.results, path))
        status[key] = "ok" if text else "pending"
        parts.append(f"## {title}\n\n" + (text or "**PENDENTE: estudo ainda não executado.**\n"))

    bench_dir = os.path.join(a.results, "benchmarks")
    if os.path.isdir(bench_dir):
        from .benchmark import summarize
        rows = []
        for d in graph_results(bench_dir):
            r = summarize(d)
            for s in ("vector", "heap"):
                stopped = [x for x in d["runs"] if x["strategy"] == s and x["status"].startswith("timeout")]
                if not r.get(f"{s}_mean_ms") and stopped:
                    r[f"{s}_limit_ms"] = stopped[0]["interrupted_after_s"] * 1000
            rows.append(r)
            missing = [s for s in ("vector", "heap") if r.get(f"{s}_runs", 0) < d["k"]]
            if missing:
                status.setdefault("incomplete_measurements", []).append(
                    {"graph": d["graph"], "strategies": missing,
                     **{f"{s}_completed": r.get(f"{s}_runs", 0) for s in ("vector", "heap")}, "k": d["k"]})
        svg = benchmark_svg(rows)
        if svg:
            with open(os.path.join(out, "benchmark.svg"), "w", encoding="utf-8") as f:
                f.write(svg)
            parts.append("![Tempo médio por origem](benchmark.svg)\n")
        parts.append("### Carga dos grafos (fora das medições)\n\n| Grafo | Leitura + construção (s) | Memória (MB) |\n|---|---|---|\n"
                     + "".join(f"| {d['graph']} | {d['load_s']:.0f} | {d['memory_mb']:.0f} |\n"
                               for d in graph_results(bench_dir)))
        env = graph_results(bench_dir)[0]["environment"] if graph_results(bench_dir) else environment()
        parts.append(f"\n### Ambiente\n\n{env['cpu']}, {env['ram_gib']} GiB RAM, {env['implementation']} "
                     f"{env['python']}, {env['platform']}.\n")
    # Tables A-D and the memory charts (read only; see experiments/tables.py)
    from . import tables
    bench = tables.benchmark_rows(a.results)
    reps = tables.representation_runs(a.results)
    parts.append("\n## Tabela A: carga dos grafos\n\n" + tables.load_table(a.results))
    parts.append("\n## Tabela B: desempenho de Dijkstra\n\n" + tables.dijkstra_table(bench))
    parts.append("\n## Tabela C: memória adicional de Dijkstra\n\n" + tables.memory_dijkstra_table(a.results))
    parts.append("\n## Tabela D: representações\n\n" + tables.representations_table(reps))
    parts.append("\n### Matriz nos grafos completos\n\n" + tables.matrix_table(bench))
    status["memory_dijkstra"] = "ok" if read_json(os.path.join(a.results, "memory_dijkstra", "runs.json")) \
        else "pending"
    status["representations"] = "ok" if reps else "pending"
    for name, svg in (("representations.svg", tables.representations_svg(reps)),
                      ("construction_peak.svg", tables.peak_svg(reps))):
        if svg:
            with open(os.path.join(out, name), "w", encoding="utf-8") as f:
                f.write(svg)
            parts.append(f"![{name}]({name})\n")
    if status.get("incomplete_measurements"):
        parts.append("\n### Medições incompletas\n\n" + "".join(
            f"- {m['graph']}: vetor {m['vector_completed']}/{m['k']}, heap {m['heap_completed']}/{m['k']} "
            "execuções concluídas.\n" for m in status["incomplete_measurements"]))
    with open(os.path.join(out, "results.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    write_json(os.path.join(out, "status.json"), status)
    print(f"{out}/results.md", status)


if __name__ == "__main__":
    main()
