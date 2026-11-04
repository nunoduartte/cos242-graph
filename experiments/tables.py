"""Tables A-D and the memory charts of the Part 2 report, read from results/part2/.

Used by experiments.report. Nothing is measured here: every number is read
from the files the studies wrote, and each derived value says what it is:
  - medido: read as is from a result file;
  - limite inferior: computed from a measured timeout (e.g. vector > 900 s
    divided by the heap time on the same source), never an estimate of the
    missing run;
  - teórico: a formula on n and m (array sizes in bytes), shown beside the
    measurement for comparison, never in its place.
MB = 2^20 bytes, as everywhere in Part 1 and Part 2.
"""
import math
import os
from html import escape

from .common import WEIGHTED_GRAPHS, graph_results, md_table, read_json

MB = 2**20
# categorical slots 1-3 of the reference chart palette (validated light-mode set)
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID = "#222222", "#666666", "#e5e5e5"
SHORT = {f"grafo_W_{i}": f"W_{i}" for i in range(3, 8)}


def br(x, digits=0):
    """Brazilian number format: 1.234,5."""
    if x is None:
        return "-"
    return f"{x:,.{digits}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def csr_bytes(n, m):
    """offsets int64 (n+2) + targets int32 and weights float64 for 2m entries."""
    return 8 * (n + 2) + 24 * m


def matrix_bytes(n):
    """bytearray presence + float64 weight per cell, (n+1)^2 cells."""
    return 9 * (n + 1) ** 2


def human_bytes(b):
    for unit, size in (("PiB", 2**50), ("TiB", 2**40), ("GiB", 2**30)):
        if b >= size:
            return f"{br(b / size, 1)} {unit}"
    return f"{br(b / MB)} MB"


def load_table(results):
    """Table A: graph loading (time and RSS after loading), with the CSR formula beside it."""
    rows = []
    for d in graph_results(os.path.join(results, "benchmarks")) if os.path.isdir(
            os.path.join(results, "benchmarks")) else []:
        rows.append([d["graph"], br(d["n"]), br(d["m"]), br(d["load_s"], 1), br(d["memory_mb"]),
                     br(csr_bytes(d["n"], d["m"]) / MB), d["representation"]])
    c = read_json(os.path.join(results, "collaboration", "result.json"))
    if c:
        rows.append(["rede_colaboracao", br(c["n"]), br(c["m"]), br(c["load_s"], 1), br(c["memory_mb"]),
                     "-", "list"])
    if not rows:
        return "**PENDENTE: nenhuma carga registrada.**\n"
    return (md_table(["Grafo", "Vértices", "Arestas", "Tempo de carga (s)", "Memória RSS (MB, medido)",
                      "CSR teórico (MB)", "Representação"], rows)
            + "\nMemória = RSS após a carga menos o RSS antes (medida da Parte 1). CSR teórico = "
              "8(n+2) + 24m bytes (fórmula, não medição).\n")


def benchmark_rows(results):
    """Summary rows of study B plus the paired lower bound when the vector timed out."""
    from .benchmark import summarize
    path = os.path.join(results, "benchmarks")
    if not os.path.isdir(path):
        return []
    rows = []
    for d in graph_results(path):
        r = summarize(d)
        ok = {(x["strategy"], x["source"]): x["seconds"] for x in d["runs"] if x["status"] == "ok"}
        for s in ("vector", "heap"):
            stopped = [x for x in d["runs"] if x["strategy"] == s and x["status"].startswith("timeout")]
            if not r.get(f"{s}_mean_ms") and stopped:
                r[f"{s}_limit_ms"] = stopped[0]["interrupted_after_s"] * 1000
                other = "heap" if s == "vector" else "vector"
                paired = ok.get((other, stopped[0]["source"]))
                if s == "vector" and paired:
                    r["speedup_lower_bound"] = stopped[0]["interrupted_after_s"] / paired
        r["not_run"] = {s: sum(1 for x in d["runs"] if x["strategy"] == s and x["status"].startswith("not run"))
                        for s in ("vector", "heap")}
        rows.append(r)
    return rows


def dijkstra_table(rows):
    """Table B: Dijkstra time, vector x heap."""
    if not rows:
        return "**PENDENTE: benchmark ainda não executado.**\n"

    def mean(r, s):
        if r.get(f"{s}_mean_ms") is not None:
            return br(r[f"{s}_mean_ms"] / 1000, 2)
        if r.get(f"{s}_limit_ms"):
            return f"> {br(r[f'{s}_limit_ms'] / 1000)} (timeout)"
        return "-"

    def speedup(r):
        if r.get("speedup"):
            return f"{br(r['speedup'])}× (medido, {r['paired_runs']} pares)"
        if r.get("speedup_lower_bound"):
            return f"> {br(r['speedup_lower_bound'], 1)}× (limite inferior)"
        return "-"
    out = md_table(["Grafo", "Vértices", "Arestas", "Execuções concluídas (vetor/heap)", "Tempo médio vetor (s)",
                    "Tempo médio heap (s)", "Speedup"],
                   [[r["graph"], br(r["n"]), br(r["m"]),
                     f"{r.get('vector_runs', 0)} / {r.get('heap_runs', 0)}", mean(r, "vector"),
                     mean(r, "heap"), speedup(r)] for r in rows])
    return out + (f"\nExecuções concluídas de k = {rows[0]['k']} origens por estratégia. Speedup medido = "
                  "média vetor / média heap nas origens concluídas pelas duas estratégias. Limite inferior = tempo em que o vetor foi interrompido / tempo do heap na mesma origem. "
                  "Execuções não concluídas: o orçamento de 1.200 s por (grafo, estratégia) acabou, ou a execução "
                  "anterior do vetor já tinha passado de 900 s; nenhuma foi estimada.\n")


def memory_dijkstra_table(results):
    """Table C: extra memory of Dijkstra (one process per strategy)."""
    data = read_json(os.path.join(results, "memory_dijkstra", "runs.json"))
    runs = data["runs"] if data else []
    rows = [[r["graph"], r["strategy"], br(r.get("rss_before_mb")), br(r.get("peak_rss_mb")),
             br(r.get("peak_increase_mb"), 1), br(r.get("dijkstra_s"), 2) if r.get("dijkstra_s") else "-",
             r["status"] + (" (tracemalloc)" if r.get("tracemalloc_peak_mb") is not None else "")] for r in runs]
    measured = {r["graph"] for r in runs}
    rows += [[g, "vetor e heap", "-", "-", "-", "-", "não medido"] for g in WEIGHTED_GRAPHS if g not in measured]
    return (md_table(["Grafo", "Estratégia", "RSS antes (MB)", "Pico RSS (MB)", "Aumento observado (MB)",
                      "Tempo (s)", "Status"], rows)
            + "\nAumento observado = pico de RSS (VmHWM zerado antes da chamada) menos o RSS antes, com o grafo "
              "já carregado. Inclui distâncias, pais e a fila; é uma aproximação do processo inteiro, não o "
              "tamanho exato das estruturas.\n")


def representation_runs(results):
    data = read_json(os.path.join(results, "representations", "runs.json"))
    return data["runs"] if data else []


def representations_table(runs):
    """Table D: list x matrix x CSR on the induced subgraphs and the whole W_3."""
    if not runs:
        return "**PENDENTE: comparação de representações ainda não executada.**\n"

    def theory(r):
        if r["representation"] == "matrix":
            return human_bytes(matrix_bytes(r["n"]))
        if r["representation"] == "csr" and r.get("m"):
            return br(csr_bytes(r["n"], r["m"]) / MB, 1) + " MB"
        return "-"
    rows = [[r["graph"], br(r.get("n")), br(r.get("m")), r["representation"],
             br(r.get("load_s"), 2) if r["status"] == "ok" else "-",
             br(r.get("graph_mb"), 1), br(r.get("peak_increase_mb"), 1), theory(r),
             "ok" if r["status"] == "ok" else r["status"]] for r in runs]
    return (md_table(["Grafo/subgrafo", "Vértices", "Arestas", "Representação", "Tempo de carga (s)",
                      "Memória (MB)", "Pico na construção (MB)", "Teórico", "Status"], rows)
            + "\nSubgrafo `_1-N` = subgrafo do W_3 induzido pelos vértices 1..N. Memória = RSS após a carga "
              "menos o RSS antes; pico = maior RSS durante leitura + construção menos o mesmo ponto. "
              "Teórico: matriz 9(n+1)² bytes, CSR 8(n+2) + 24m bytes.\n")


def matrix_table(bench_rows):
    """Matrix size of every official graph: theory only, never built."""
    if not bench_rows:
        return ""
    return (md_table(["Grafo", "Vértices", "Matriz com pesos (teórico)", "Situação"],
                     [[r["graph"], br(r["n"]), human_bytes(matrix_bytes(r["n"])), "não construída"]
                      for r in bench_rows])
            + "\n9(n+1)² bytes (fórmula, não medição).\n")


def representations_svg(runs) -> str:
    """Memory after loading vs n (log-log), one line per representation; the matrix
    of the whole W_3 is drawn as an open marker at its formula size (not built)."""
    by = {}
    for r in runs:
        if r["status"] == "ok":
            by.setdefault(r["representation"], []).append((r["n"], max(r["graph_mb"], 0.1)))
        elif r["representation"] == "matrix":
            by.setdefault("matrix_theory", []).append((r["n"], matrix_bytes(r["n"]) / MB))
    if not by:
        return ""
    width, height, left, right, top, bottom = 760, 400, 70, 150, 80, 330
    xs = [n for pts in by.values() for n, _ in pts]
    ys = [v for pts in by.values() for _, v in pts]
    x_lo, x_hi = math.log10(min(xs)) - 0.1, math.log10(max(xs)) + 0.1
    y_lo, y_hi = math.floor(math.log10(min(ys))), math.ceil(math.log10(max(ys)))
    X = lambda n: left + (math.log10(n) - x_lo) / (x_hi - x_lo) * (width - left - right)
    Y = lambda v: bottom - (math.log10(v) - y_lo) / (y_hi - y_lo) * (bottom - top)
    out = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {width} {height}' font-family='sans-serif' "
           f"font-size='12'><rect width='100%' height='100%' fill='white'/>",
           f"<text x='{left}' y='22' font-size='15' fill='{INK}'>Memória após a carga por representação "
           f"(MB, escala log-log)</text>",
           f"<text x='{left}' y='38' fill='{MUTED}' font-size='11'>Subgrafos induzidos do W_3 e W_3 completo; "
           f"medição de RSS, um processo por ponto</text>"]
    for e in range(y_lo, y_hi + 1):
        out.append(f"<line x1='{left}' x2='{width - right}' y1='{Y(10**e):.1f}' y2='{Y(10**e):.1f}' "
                   f"stroke='{GRID}'/><text x='{left - 6}' y='{Y(10**e) + 4:.1f}' text-anchor='end' "
                   f"fill='{MUTED}'>{br(10**e, max(0, -e))}</text>")
    for n in sorted(set(xs)):
        out.append(f"<text x='{X(n):.1f}' y='{bottom + 18}' text-anchor='middle' fill='{MUTED}'>{br(n)}</text>")
    out.append(f"<text x='{(left + width - right) / 2:.1f}' y='{bottom + 38}' text-anchor='middle' "
               f"fill='{MUTED}'>vértices (n)</text>")
    names = {"list": ("lista", BLUE), "matrix": ("matriz", ORANGE), "csr": ("CSR", AQUA)}
    label_dy = {"list": -8, "csr": 14, "matrix": -8}
    for rep, (label, color) in names.items():
        pts = sorted(by.get(rep, []))
        if not pts:
            continue
        path = " ".join(f"{'M' if i == 0 else 'L'}{X(n):.1f},{Y(v):.1f}" for i, (n, v) in enumerate(pts))
        out.append(f"<path d='{path}' fill='none' stroke='{color}' stroke-width='2'/>")
        for n, v in pts:
            out.append(f"<circle cx='{X(n):.1f}' cy='{Y(v):.1f}' r='4' fill='{color}' stroke='white' "
                       f"stroke-width='2'><title>{label}, n = {br(n)}: {br(v, 1)} MB (medido)</title></circle>")
        n, v = pts[-1]
        anchor, dx = ("end", -8) if rep == "matrix" else ("start", 8)  # the matrix line continues dashed
        out.append(f"<text x='{X(n) + dx:.1f}' y='{Y(v) + label_dy[rep]:.1f}' text-anchor='{anchor}' "
                   f"fill='{INK}'>{label} {br(v)} MB</text>")
    for n, v in by.get("matrix_theory", []):
        last = sorted(by.get("matrix", []))[-1] if by.get("matrix") else None
        if last:
            out.append(f"<line x1='{X(last[0]):.1f}' y1='{Y(last[1]):.1f}' x2='{X(n):.1f}' y2='{Y(v):.1f}' "
                       f"stroke='{ORANGE}' stroke-width='2' stroke-dasharray='5 4'/>")
        out.append(f"<circle cx='{X(n):.1f}' cy='{Y(v):.1f}' r='5' fill='white' stroke='{ORANGE}' "
                   f"stroke-width='2'><title>matriz, n = {br(n)}: {human_bytes(matrix_bytes(n))} "
                   f"(teórico, não construída)</title></circle>"
                   f"<text x='{X(n) + 9:.1f}' y='{Y(v) + 4:.1f}' fill='{INK}'>matriz {human_bytes(matrix_bytes(n))}"
                   f"</text><text x='{X(n) + 9:.1f}' y='{Y(v) + 18:.1f}' fill='{MUTED}' font-size='11'>teórico, "
                   f"não construída</text>")
    lx = left
    for rep, (label, color) in names.items():
        out.append(f"<rect x='{lx}' y='50' width='12' height='12' rx='2' fill='{color}'/>"
                   f"<text x='{lx + 17}' y='60' fill='{INK}'>{label}</text>")
        lx += 80
    out.append(f"<text x='{left}' y='{height - 10}' fill='{MUTED}' font-size='11'>Marcador vazado e linha "
               f"tracejada: fórmula 9(n+1)² bytes, matriz não construída (não medido).</text></svg>")
    return "\n".join(out)


def peak_svg(runs) -> str:
    """After-load vs construction-peak memory of list and CSR on the largest graph measured (grouped bars)."""
    ok = [r for r in runs if r["status"] == "ok" and r["representation"] in ("list", "csr")]
    if not ok:
        return ""
    graph = max(ok, key=lambda r: r["n"])["graph"]
    sel = [r for r in ok if r["graph"] == graph]
    width, height, left, top, bottom = 760, 290, 70, 70, 250
    hi = max(r["peak_increase_mb"] for r in sel)
    step = 100 if hi > 200 else 10
    top_v = math.ceil(hi / step) * step
    Y = lambda v: bottom - v / top_v * (bottom - top)
    out = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {width} {height}' font-family='sans-serif' "
           f"font-size='12'><rect width='100%' height='100%' fill='white'/>",
           f"<text x='{left}' y='22' font-size='15' fill='{INK}'>{escape(graph)}: memória após a carga x pico "
           f"durante a construção (MB)</text>",
           f"<rect x='{left}' y='34' width='12' height='12' rx='2' fill='{BLUE}'/><text x='{left + 17}' y='44' "
           f"fill='{INK}'>após a carga</text><rect x='{left + 120}' y='34' width='12' height='12' rx='2' "
           f"fill='{ORANGE}'/><text x='{left + 137}' y='44' fill='{INK}'>pico na construção</text>"]
    v = 0
    while v <= top_v:
        out.append(f"<line x1='{left}' x2='{width - 20}' y1='{Y(v):.1f}' y2='{Y(v):.1f}' stroke='{GRID}'/>"
                   f"<text x='{left - 6}' y='{Y(v) + 4:.1f}' text-anchor='end' fill='{MUTED}'>{br(v)}</text>")
        v += step
    band = (width - left - 20) / len(sel)
    bar = min(80, band / 3)
    for i, r in enumerate(sorted(sel, key=lambda r: r["representation"] != "list")):
        cx = left + band * i + band / 2
        for j, (key, color) in enumerate((("graph_mb", BLUE), ("peak_increase_mb", ORANGE))):
            val = r[key]
            x = cx - bar - 1 + j * (bar + 2)
            out.append(f"<path d='M{x:.1f},{bottom} V{Y(val) + 4:.1f} q0,-4 4,-4 H{x + bar - 4:.1f} q4,0 4,4 "
                       f"V{bottom} Z' fill='{color}'><title>{r['representation']}: {br(val, 1)} MB "
                       f"(medido)</title></path><text x='{x + bar / 2:.1f}' y='{Y(val) - 6:.1f}' "
                       f"text-anchor='middle' fill='{INK}'>{br(val)}</text>")
        out.append(f"<text x='{cx:.1f}' y='{bottom + 20}' text-anchor='middle' fill='{INK}'>"
                   f"{'lista' if r['representation'] == 'list' else 'CSR'}</text>")
    out.append(f"<line x1='{left}' x2='{width - 20}' y1='{bottom}' y2='{bottom}' stroke='#999'/></svg>")
    return "\n".join(out)
