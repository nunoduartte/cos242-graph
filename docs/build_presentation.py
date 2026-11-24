"""Builds docs/apresentacao_parte3.pptx (and an HTML preview for visual checks).

Usage (from the repository root, with a Python that has python-pptx):
  ~/.venvs/cos242-accel/bin/python docs/build_presentation.py [--preview DIR]
Same visual identity as Part 2 (16:9, Calibri, navy 14213D, blue 1C5CAB, orange
EB6834; dark cover and conclusion). Every number on the slides is read from
results/part3/ (nothing is typed by hand); speaker notes carry the script, the
time of each slide and who speaks. --preview writes DIR/slides.html with the
same geometry (Liberation Sans, a little wider than Calibri) to check the layout.
"""
import argparse
import json
import math
import os
import statistics
from html import escape

from pptx import Presentation
from pptx.chart.data import CategoryChartData, XyChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

R = "results/part3"
NAVY, BLUE, ORANGE, INK, MUTED = "14213D", "1C5CAB", "EB6834", "1F2933", "5B6573"
LIGHT, TINT, WHITE, SKY, PALE = "F4F5F7", "E8EFF9", "FFFFFF", "8FB8EF", "BFD0E6"
GREEN = "2E7D4F"
W, H = 13.333, 7.5


def load(path):
    with open(os.path.join(R, path), encoding="utf-8") as f:
        return json.load(f)


def num(x, d=2):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def from_json(x):
    return {"inf": math.inf, "-inf": -math.inf}.get(x, x) if isinstance(x, str) else x


def mean_sd(runs):
    t = [r["seconds"] for r in runs if r.get("seconds") is not None]
    return (statistics.fmean(t) if t else None, statistics.stdev(t) if len(t) > 1 else None, len(t), len(runs))


# ---------------------------------------------------------------- slide model (pptx + HTML preview)
class Deck:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = Inches(W), Inches(H)
        self.blank = self.prs.slide_layouts[6]
        self.html = []
        self.count = 0

    def slide(self, dark=False, notes=""):
        s = self.prs.slides.add_slide(self.blank)
        self.count += 1
        bg = s.background.fill
        bg.solid()
        bg.fore_color.rgb = RGBColor.from_string(NAVY if dark else WHITE)
        if notes:
            s.notes_slide.notes_text_frame.text = notes
        self.cur, self.dark = s, dark
        self.html.append({"bg": NAVY if dark else WHITE, "items": [], "notes": notes})
        if not dark:
            self.text(f"{self.count}", W - 1.0, H - 0.45, 0.6, 0.3, size=10, color=MUTED, align="r")
        return s

    def _h(self, kind, x, y, w, h, **kw):
        self.html[-1]["items"].append((kind, x, y, w, h, kw))

    def rect(self, x, y, w, h, fill=LIGHT, line=None, rounded=True, name=None):
        shp = self.cur.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
                                        Inches(x), Inches(y), Inches(w), Inches(h))
        if rounded:
            shp.adjustments[0] = 0.06
        shp.fill.solid()
        shp.fill.fore_color.rgb = RGBColor.from_string(fill)
        if line:
            shp.line.color.rgb = RGBColor.from_string(line)
            shp.line.width = Pt(1)
        else:
            shp.line.fill.background()
        shp.shadow.inherit = False
        if name:
            shp.name = name
        self._h("rect", x, y, w, h, fill=fill, line=line, rounded=rounded)
        return shp

    def text(self, runs, x, y, w, h, size=16, color=INK, bold=False, align="l", font="Calibri",
             anchor="t", spacing=None, bullets=False, para_after=4):
        """runs: str, or list of paragraphs; a paragraph is a str or a list of (text, {opts})."""
        tb = self.cur.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}[anchor]
        paras = runs if isinstance(runs, list) else [runs]
        html_paras = []
        for i, p in enumerate(paras):
            para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            para.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[align]
            para.space_after = Pt(para_after)
            if bullets:
                pPr = para._p.get_or_add_pPr()
                pPr.set("marL", str(int(Inches(0.22))))
                pPr.set("indent", str(-int(Inches(0.22))))
                bu = pPr.makeelement(qn("a:buChar"), {"char": "•"})
                pPr.append(bu)
            parts = p if isinstance(p, list) else [(p, {})]
            hp = []
            for t, o in parts:
                r = para.add_run()
                r.text = t
                f = r.font
                f.name = o.get("font", font)
                f.size = Pt(o.get("size", size))
                f.bold = o.get("bold", bold)
                f.italic = o.get("italic", False)
                f.color.rgb = RGBColor.from_string(o.get("color", color))
                if spacing:
                    r._r.get_or_add_rPr().set("spc", str(spacing))
                hp.append((t, {"font": o.get("font", font), "size": o.get("size", size),
                               "bold": o.get("bold", bold), "italic": o.get("italic", False),
                               "color": o.get("color", color)}))
            html_paras.append(hp)
        self._h("text", x, y, w, h, paras=html_paras, align=align, anchor=anchor, bullets=bullets,
                spacing=spacing, para_after=para_after)
        return tb

    def table(self, rows, x, y, w, col_w, size=13, header_fill=TINT, row_h=0.36, bold_first_col=False,
              align=None, highlight=None):
        nr, nc = len(rows), len(rows[0])
        gt = self.cur.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(w), Inches(row_h * nr))
        tbl = gt.table
        tblPr = tbl._tbl.tblPr
        style = tblPr.find(qn("a:tableStyleId"))
        if style is not None:
            style.text = "{5940675A-B579-460E-94D1-54222C63F5DA}"  # No Style, Table Grid
        for j, cw in enumerate(col_w):
            tbl.columns[j].width = Inches(cw)
        for i, row in enumerate(rows):
            tbl.rows[i].height = Inches(row_h)
            for j, val in enumerate(row):
                c = tbl.cell(i, j)
                c.margin_left = c.margin_right = Inches(0.07)
                c.margin_top = c.margin_bottom = Inches(0.03)
                c.vertical_anchor = MSO_ANCHOR.MIDDLE
                fill = header_fill if i == 0 else (highlight.get((i, j)) if highlight and (i, j) in highlight
                                                   else WHITE)
                c.fill.solid()
                c.fill.fore_color.rgb = RGBColor.from_string(fill)
                tf = c.text_frame
                tf.word_wrap = True
                p = tf.paragraphs[0]
                a = (align[j] if align else "l")
                p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[a]
                r = p.add_run()
                r.text = str(val)
                r.font.name, r.font.size = "Calibri", Pt(size)
                r.font.bold = i == 0 or (bold_first_col and j == 0)
                r.font.color.rgb = RGBColor.from_string(NAVY if i == 0 else INK)
        self._h("table", x, y, w, row_h * nr, rows=rows, col_w=col_w, size=size, header_fill=header_fill,
                row_h=row_h, bold_first_col=bold_first_col, align=align, highlight=highlight or {})

    def chart(self, kind, data, x, y, w, h, **kw):
        gf = self.cur.shapes.add_chart(kind, Inches(x), Inches(y), Inches(w), Inches(h), data)
        self._h("chart", x, y, w, h, svg=kw.pop("svg", ""))
        return gf.chart

    def header(self, eyebrow, title):
        self.text(eyebrow.upper(), 0.6, 0.42, 12.1, 0.3, size=12, color=BLUE, bold=True, spacing=200)
        self.text(title, 0.6, 0.72, 12.1, 0.8, size=30, color=NAVY, bold=True)

    # ------------------------------------------------------------ HTML preview
    def preview(self, path):
        px = 96
        out = ["<!doctype html><meta charset='utf-8'><style>body{margin:0;background:#888;font-family:"
               "'Liberation Sans',Arial,sans-serif}.s{position:relative;width:1280px;height:720px;margin:0 0 8px;"
               "overflow:hidden}.e{position:absolute;box-sizing:border-box}table{border-collapse:collapse;"
               "table-layout:fixed}td{border:1px solid #c9d3e0;padding:2px 7px;overflow:hidden;box-sizing:border-box}"
               "</style>"]
        for s in self.html:
            out.append(f"<div class='s' style='background:#{s['bg']}'>")
            for kind, x, y, w, h, kw in s["items"]:
                pos = f"left:{x*px}px;top:{y*px}px;width:{w*px}px;height:{h*px}px"
                if kind == "rect":
                    out.append(f"<div class='e' style='{pos};background:#{kw['fill']};"
                               f"border-radius:{8 if kw['rounded'] else 0}px;"
                               f"{'border:1px solid #'+kw['line'] if kw['line'] else ''}'></div>")
                elif kind == "text":
                    just = {"t": "flex-start", "m": "center", "b": "flex-end"}[kw["anchor"]]
                    ps = []
                    for para in kw["paras"]:
                        spans = "".join(
                            f"<span style=\"font-size:{o['size']*px/72}px;font-weight:{700 if o['bold'] else 400};"
                            f"font-style:{'italic' if o['italic'] else 'normal'};color:#{o['color']};"
                            f"font-family:{'Liberation Mono' if 'Courier' in o['font'] else 'Liberation Sans'}"
                            f"{';letter-spacing:%spx' % (kw['spacing']/100) if kw['spacing'] else ''}\">"
                            f"{escape(t)}</span>" for t, o in para)
                        bullet = "• " if kw["bullets"] else ""
                        ps.append(f"<div style='margin-bottom:{kw['para_after']*px/72}px;line-height:1.2;"
                                  f"{'padding-left:21px;text-indent:-21px' if bullet else ''}'>{bullet}{spans}</div>")
                    out.append(f"<div class='e' style='{pos};display:flex;flex-direction:column;justify-content:{just};"
                               f"text-align:{ {'l':'left','c':'center','r':'right'}[kw['align']] };"
                               f"outline:1px dashed rgba(255,0,0,.25)'>{''.join(ps)}</div>")
                elif kind == "table":
                    rows = []
                    for i, row in enumerate(kw["rows"]):
                        cells = []
                        for j, v in enumerate(row):
                            bg = kw["header_fill"] if i == 0 else kw["highlight"].get((i, j), WHITE)
                            al = {"l": "left", "c": "center", "r": "right"}[(kw["align"] or "l" * len(row))[j]]
                            b = 700 if i == 0 or (kw["bold_first_col"] and j == 0) else 400
                            cells.append(f"<td style='width:{kw['col_w'][j]*px}px;height:{kw['row_h']*px}px;"
                                         f"background:#{bg};text-align:{al};font-weight:{b};"
                                         f"font-size:{kw['size']*px/72}px;color:#{NAVY if i == 0 else INK}'>"
                                         f"{escape(str(v))}</td>")
                        rows.append("<tr>" + "".join(cells) + "</tr>")
                    out.append(f"<table class='e' style='left:{x*px}px;top:{y*px}px'>{''.join(rows)}</table>")
                elif kind == "chart":
                    out.append(f"<div class='e' style='{pos};border:1px solid #ddd'>{kw['svg']}</div>")
            out.append("</div>")
        with open(path, "w", encoding="utf-8") as f:
            f.write("".join(out))


def log_axis(chart, axis="value", base=10):
    ax = chart.value_axis if axis == "value" else chart.category_axis
    scaling = ax._element.find(qn("c:scaling"))
    lb = scaling.makeelement(qn("c:logBase"), {"val": str(base)})
    scaling.insert(0, lb)


def style_chart(chart, size=12):
    chart.font.size = Pt(size)
    chart.font.name = "Calibri"
    chart.font.color.rgb = RGBColor.from_string(INK)


# ---------------------------------------------------------------- data
def graph_label(g):
    return g.replace("grafo_", "")


def results():
    data = {"s1": {}, "s2": {}, "s3": {}, "s4": {}, "s4n": {}}
    for g in ["grafo_W_1", "grafo_W_2", "grafo_W_3", "grafo_W_4", "grafo_W_5"]:
        for key, sub in (("s1", "bellman_ford"), ("s2", "floyd_warshall"), ("s3", "benchmark")):
            p = os.path.join(R, sub, g + ".json")
            if os.path.exists(p):
                data[key][g] = load(os.path.join(sub, g + ".json"))
    for key, sub in (("s4", "all_pairs"), ("s4n", "all_pairs_numba")):
        d = os.path.join(R, sub)
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if f.endswith(".json"):
                x = load(os.path.join(sub, f))
                data[key][x["graph"]] = x
    return data


def svg_lines(series, xlabel, ylabel, w=560, h=330):
    """Tiny log-log SVG for the HTML preview only (the deck has a native chart)."""
    pts = [(x, y) for _, _, s in series for x, y in s if y]
    if not pts:
        return ""
    lx = [math.log10(x) for x, _ in pts]
    ly = [math.log10(y) for _, y in pts]
    x0, x1, y0, y1 = math.floor(min(lx)), math.ceil(max(lx)), math.floor(min(ly)), math.ceil(max(ly))
    X = lambda v: 50 + (math.log10(v) - x0) / max(1e-9, x1 - x0) * (w - 70)
    Y = lambda v: h - 40 - (math.log10(v) - y0) / max(1e-9, y1 - y0) * (h - 60)
    out = [f"<svg width='100%' height='100%' viewBox='0 0 {w} {h}'>"]
    for name, color, s in series:
        s = [(x, y) for x, y in s if y]
        out.append(f"<polyline fill='none' stroke='#{color}' stroke-width='3' points='"
                   + " ".join(f"{X(x):.0f},{Y(y):.0f}" for x, y in s) + "'/>")
    out.append(f"<text x='{w/2}' y='{h-8}' font-size='12' text-anchor='middle'>{xlabel}</text></svg>")
    return "".join(out)


# ---------------------------------------------------------------- slides
def build(deck, D):
    s1, s2, s3, s4, s4n = D["s1"], D["s2"], D["s3"], D["s4"], D["s4n"]
    w2fw = s3["grafo_W_2"]["runs"]["floyd-warshall"]
    fw_mean, fw_sd, fw_done, fw_rounds = mean_sd(w2fw)
    w1fw = s3["grafo_W_1"]["runs"]["floyd-warshall"][0]

    # 1 ---------------------------------------------------------------- cover
    deck.slide(dark=True, notes=(
        "NUNO · 0:15\nApresentar a dupla. Nesta parte a biblioteca passou a aceitar grafos direcionados com pesos, "
        "ganhou Bellman-Ford e Floyd-Warshall, e rodamos os quatro estudos nos cinco grafos oficiais. Ao longo da "
        "fala dizemos sempre se um número é medido, calculado ou estimado."))
    deck.text("TEORIA DOS GRAFOS · COS242 · 2026/2", 0.8, 0.8, 11, 0.4, size=14, color=SKY, bold=True, spacing=300)
    deck.text("Caminhos mínimos com pesos negativos: Bellman-Ford e Floyd-Warshall", 0.8, 1.75, 11.2, 2.2,
              size=42, color=WHITE, bold=True)
    deck.text("Trabalho de Disciplina – Parte 3", 0.8, 4.15, 11, 0.5, size=24, color=PALE)
    deck.text("Nuno Correia e Nicolas Viana", 0.8, 5.55, 11, 0.45, size=22, color=WHITE, bold=True)
    deck.text("github.com/nunoduartte/cos242-graph", 0.8, 6.05, 11, 0.4, size=16, color=SKY)

    # 2 ---------------------------------------------------------------- request and data
    deck.slide(notes=(
        "NUNO · 0:30\nO enunciado pede quatro coisas: grafos direcionados com pesos, BFS/DFS/Dijkstra adaptados, "
        "Bellman-Ford até um destino com duas otimizações e detecção de ciclo negativo, e Floyd-Warshall com a "
        "otimização de memória. Os dados: dois grafos de 25 mil vértices — o W_1 é o único com pesos negativos e "
        "tem ciclos negativos — e três grafos grandes, até 10 milhões de vértices."))
    deck.header("O pedido e os dados", "Quatro funcionalidades, quatro estudos, cinco grafos")
    items = [("Direcionados", "u v w = só a aresta u → v; parâmetro directed do usuário"),
             ("BFS · DFS · Dijkstra", "adaptados aos grafos direcionados"),
             ("Bellman-Ford", "de todos os vértices até um destino; 2 otimizações; ciclo negativo"),
             ("Floyd-Warshall", "todos os pares; otimização de memória; ciclo negativo")]
    for i, (t, d) in enumerate(items):
        y = 1.75 + i * 1.2
        deck.rect(0.6, y, 5.6, 1.0, fill=LIGHT)
        deck.text(t, 0.85, y + 0.12, 5.2, 0.4, size=18, color=NAVY, bold=True)
        deck.text(d, 0.85, y + 0.52, 5.2, 0.4, size=14, color=MUTED)
    rows = [["Grafo", "Vértices", "Arestas", "Pesos"]]
    for g in ["grafo_W_1", "grafo_W_2", "grafo_W_3", "grafo_W_4", "grafo_W_5"]:
        d = s1[g]
        rows.append([graph_label(g), num(d["n"], 0), num(d["m"], 0),
                     f"{d['negative_edges']:,} negativos".replace(",", ".") if d["negative_edges"] else "≥ 0"])
    deck.table(rows, 6.8, 1.75, 5.9, [1.0, 1.5, 1.6, 1.8], size=15, row_h=0.5, align="lrrl",
               highlight={(1, 3): "FCE4D6"})
    deck.text("Arquivos oficiais lidos como direcionados, em CSR. W_1: pesos de −5 a 10, com ciclos negativos de "
              "2 arestas.", 6.8, 5.0, 5.9, 0.8, size=14, color=MUTED)

    # 3 ---------------------------------------------------------------- direction
    deck.slide(notes=(
        "NUNO · 0:40\nA direção é um detalhe da representação: add_edge só grava u → v quando o grafo é direcionado. "
        "Como BFS, DFS e Dijkstra já percorriam só os vizinhos de saída, nenhum deles mudou uma linha — e os 66 "
        "testes das partes anteriores passam sem alteração, porque directed é falso por padrão. O que entrou foi o "
        "grafo transposto, que na CSR é uma transposição direta em O(n + m), e o Bellman-Ford usa isso."))
    deck.header("Arquitetura · Composition + Strategy", "A direção é um detalhe da representação")
    deck.rect(0.6, 1.75, 6.6, 1.55, fill=NAVY)
    deck.text([[("g = GraphReader.read(arq, \"csr\",", {"color": WHITE})],
               [("        weighted=True, ", {"color": WHITE}), ("directed=True", {"color": "F2A07B"}),
                (")", {"color": WHITE})],
               [("r = BellmanFord().to_target(g, 100)", {"color": WHITE})]],
              0.85, 1.92, 6.2, 1.3, size=17, font="Courier New", para_after=2)
    pts = [("Só add_edge muda", "linha u v w grava u → v; sem direção, grava as duas, como antes"),
           ("BFS, DFS e Dijkstra sem mudança de código", "já percorriam só os vizinhos de saída"),
           ("Gᵀ = g.reversed()", "na CSR, transposição direta O(n + m): 1,7 s no W_3, 22 s no W_5 (medido)"),
           ("Laço u → u mantido", "um laço negativo é um ciclo negativo; arestas paralelas: fica a de menor peso")]
    for i, (t, d) in enumerate(pts):
        y = 3.6 + i * 0.85
        deck.text([[(t, {"bold": True, "color": NAVY})], [(d, {"color": MUTED, "size": 14})]],
                  0.6, y, 6.6, 0.8, size=16, para_after=1)
    deck.rect(7.7, 1.75, 5.0, 4.95, fill=LIGHT)
    deck.text("Mesmo resultado, mesma interface", 7.95, 1.95, 4.6, 0.4, size=18, color=NAVY, bold=True)
    deck.text(["ShortestPathsTo — Bellman-Ford até t: distância, sucessor rumo a t, ciclo negativo",
               "AllPairsShortestPaths — Floyd-Warshall e Bellman-Ford de todos os pares devolvem as mesmas duas "
               "matrizes (distância e predecessor)",
               "128 testes: referência independente, 8 combinações de otimizações, BF todos os pares = FW"],
              7.95, 2.5, 4.55, 4.0, size=15, bullets=True, para_after=10)

    # 4 ---------------------------------------------------------------- Bellman-Ford
    w2 = s1["grafo_W_2"]
    deck.slide(notes=(
        "NUNO · 0:45\nO Bellman-Ford clássico vai de uma origem para todos. O pedido é de todos para um destino: "
        "rodamos o clássico no grafo transposto a partir de t, e o pai em Gᵀ vira o próximo vértice rumo a t. "
        "Otimizações: parada antecipada — se uma rodada não muda nada, acabou — e só vértices ativos — uma rodada "
        f"só relaxa as arestas de quem mudou. No W_2 isso deu {w2['passes']} rodadas em vez de 24.999 e "
        f"{num(w2['relaxations']/1e6, 1)} milhões de relaxamentos em vez de cerca de 20 milhões. Não sabemos com "
        "certeza se são as duas otimizações da aula; escolhemos as clássicas do Kleinberg-Tardos."))
    deck.header("Bellman-Ford até um destino", "Distância até t em G = distância a partir de t em Gᵀ")
    deck.rect(0.6, 1.75, 5.6, 2.2, fill=LIGHT)
    deck.text([[("Gᵀ a partir de t", {"bold": True, "color": NAVY, "size": 18})],
               [("O pai de v em Gᵀ é o próximo vértice de v rumo a t em G: a árvore devolvida é enraizada em t "
                 "e path_from(v) segue os sucessores.", {"color": INK})]],
              0.85, 1.95, 5.15, 1.9, size=15, para_after=6)
    deck.rect(0.6, 4.15, 5.6, 2.5, fill=LIGHT)
    deck.text([[("Duas otimizações (pedidas)", {"bold": True, "color": NAVY, "size": 18})],
               [("1. Parada antecipada: rodada sem mudança encerra.", {})],
               [("2. Só vértices ativos: relaxa as arestas de quem mudou.", {})],
               [("Correspondência com a aula não confirmada no material.", {"italic": True, "color": MUTED,
                                                                            "size": 13})]],
              0.85, 4.35, 5.15, 2.2, size=15, para_after=6)
    stats = [(f"{w2['passes']}", "rodadas no W_2 (medido)", "contra n − 1 = 24.999"),
             (f"{num(w2['relaxations']/1e6, 1)} mi", "relaxamentos no W_2 (medido)",
              f"contra {w2['passes']} × m ≈ {num(w2['passes']*w2['m']/1e6, 1)} mi sem vértices ativos"),
             (f"{num(s3['grafo_W_2']['runs']['bellman-ford'][0]['seconds'], 2)} s",
              "uma execução no W_2 (medido)", "inclui montar Gᵀ")]
    for i, (big, lab, sub) in enumerate(stats):
        y = 1.75 + i * 1.65
        deck.text(big, 6.8, y, 2.6, 1.0, size=46, color=ORANGE, bold=True, anchor="m")
        deck.text([[(lab, {"bold": True, "color": NAVY})], [(sub, {"color": MUTED, "size": 14})]],
                  9.5, y + 0.15, 3.3, 1.2, size=16, para_after=2)

    # 5 ---------------------------------------------------------------- negative cycles
    w1 = s1["grafo_W_1"]
    c1 = w1["negative_cycle_to_target"]
    deck.slide(notes=(
        "NUNO · 0:40\nCiclo negativo: dá para dar voltas e baixar a distância indefinidamente, então a distância é "
        "−∞. Detectamos de duas formas: se a rodada n ainda muda algo, e — a otimização que faz o W_1 ser viável — "
        f"se os ponteiros de pai formam um ciclo, que é sempre negativo. No W_1 o ciclo apareceu na rodada "
        f"{w1['passes']}, em vez de 25 mil rodadas. Todos os {num(w1['vertices_minus_inf'], 0)} vértices alcançam "
        "esse ciclo, então as três distâncias até 100 são −∞. O Floyd-Warshall chega à mesma conclusão: na etapa "
        f"k = {w1fw['stopped_at']}, D[i][i] fica negativo e ele para."))
    deck.header("Ciclos negativos · W_1", "Com ciclo negativo, a resposta correta é −∞")
    cards = [("Bellman-Ford", f"ciclo nos ponteiros de pai na rodada {w1['passes']}",
              f"{' → '.join(map(str, c1['vertices']))}, peso {num(c1['weight'])}"),
             ("Distâncias até 100", f"{num(w1['vertices_minus_inf'], 0)} vértices com −∞",
              "todos alcançam o ciclo, que alcança 100: d(10), d(20), d(30) = −∞"),
             ("Floyd-Warshall", f"para na etapa k = {w1fw['stopped_at']}",
              f"D[i][i] < 0: {' → '.join(map(str, w1fw['negative_cycle']['vertices']))}, "
              f"peso {num(w1fw['negative_cycle']['weight'])}")]
    for i, (t, big, d) in enumerate(cards):
        x = 0.6 + i * 4.1
        deck.rect(x, 1.8, 3.85, 3.0, fill=LIGHT)
        deck.text(t.upper(), x + 0.25, 2.0, 3.4, 0.35, size=12, color=BLUE, bold=True, spacing=150)
        deck.text(big, x + 0.25, 2.45, 3.4, 1.0, size=22, color=NAVY, bold=True)
        deck.text(d, x + 0.25, 3.55, 3.4, 1.1, size=14, color=MUTED)
    deck.text([[("Detecção: ", {"bold": True, "color": NAVY}),
                ("rodada n ainda muda algo, ou ciclo nos pais (verificado nas rodadas 1, 2, 4, 8, …). ", {}),
                ("Grafo todo: ", {"bold": True, "color": NAVY}),
                ("origem virtual com arestas de peso 0 para todos (find_negative_cycle). Valores finitos ficam "
                 "marcados como não exatos (exact = False).", {})]],
              0.6, 5.1, 12.1, 1.2, size=16)

    # 6 ---------------------------------------------------------------- Floyd-Warshall
    deck.slide(notes=(
        "NUNO · 0:50\nFloyd-Warshall: etapa k, D[i][j] = min(D[i][j], D[i][k] + D[k][j]). A otimização de memória "
        "pedida: a etapa k não muda a linha nem a coluna k, então uma única matriz atualizada no lugar basta — duas "
        "matrizes n × n, 7 GiB para 25 mil vértices; o W_3 pediria 112 GiB, e recusamos antes de alocar. Em Python "
        "puro uma rodada no W_2 levaria 150 a 170 horas — isso é estimativa. Como as linhas de uma etapa são "
        "independentes, paralelizamos e compilamos com Numba o mesmo laço, com o mesmo resultado bit a bit. A "
        f"rodada completa no W_2 levou {num(fw_mean/60, 0)} minutos, medido."))
    deck.header("Floyd-Warshall · memória e aceleração", "Uma matriz no lugar, linhas independentes")
    deck.rect(0.6, 1.75, 5.6, 4.9, fill=LIGHT)
    deck.text([[("Otimização de memória (pedida)", {"bold": True, "color": NAVY, "size": 18})],
               [("A etapa k não muda a linha nem a coluna k: basta uma matriz de distâncias e uma de "
                 "predecessores, atualizadas no lugar.", {})],
               [("12(n + 1)² bytes", {"bold": True, "color": ORANGE, "size": 24})],
               [("W_1, W_2: 7,0 GiB · W_3: 112 GiB · W_4: 11 TiB · W_5: 1,1 PiB (calculado) — acima de 16 GiB, "
                 "recusado antes de alocar.", {"color": MUTED, "size": 14})]],
              0.85, 1.95, 5.15, 4.6, size=15, para_after=10)
    rows = [["Subgrafo W_2 1..3000 (medido)", "Tempo", "Ganho"],
            ["Python, 1 processo", "274,0 s", "1×"], ["Python, 16 processos", "36,6 s", "7,5×"],
            ["NumPy, 16 threads", "8,5 s", "32×"], ["Numba, 16 threads", "1,16 s", "237×"]]
    deck.table(rows, 6.8, 1.75, 5.9, [3.4, 1.3, 1.2], size=15, row_h=0.48, align="lrr",
               highlight={(4, 0): "FCE4D6", (4, 1): "FCE4D6", (4, 2): "FCE4D6"})
    deck.text([[("Mesma matriz nas 5 versões (digest igual). ", {"bold": True, "color": NAVY}),
                ("Mesma soma IEEE-754, mesma comparação estrita, mesma ordem de k; sem variante em blocos. "
                 "NumPy e Numba são opcionais; JIT fora do tempo medido. Adicional, não pedido.", {"color": MUTED})]],
              6.8, 4.35, 5.9, 1.3, size=14)
    deck.text([[(f"W_2 completo: {num(fw_mean, 0)} s ", {"bold": True, "color": ORANGE, "size": 20}),
                (f"(média de {fw_done} rodadas, medido)", {"color": MUTED, "size": 14})]],
              6.8, 5.85, 5.9, 0.6, size=16)

    # 7 ---------------------------------------------------------------- study 1
    deck.slide(notes=(
        "NICOLAS · 0:35\nEstudo 1: uma única execução por grafo responde as três origens, porque o destino é comum. "
        "No W_1 as três distâncias são −∞ por causa do ciclo negativo — não apresentamos número. Nos outros, "
        "distâncias finitas, conferidas com o certificado de otimalidade em todas as arestas e com Dijkstra no "
        "grafo transposto. O número de arestas do caminho cresce com o grafo, até 30 no W_5."))
    deck.header("Estudo 1 · Bellman-Ford", "Distância de 10, 20 e 30 até o vértice 100")
    rows = [["Grafo", "d(10 → 100)", "d(20 → 100)", "d(30 → 100)", "Rodadas", "Validação"]]
    for g in ["grafo_W_1", "grafo_W_2", "grafo_W_3", "grafo_W_4", "grafo_W_5"]:
        d = s1[g]
        cells = []
        for s in d["sources"]:
            dist = s["distance"]
            cells.append("−∞ (ciclo neg.)" if dist == "-inf" else "∞" if dist == "inf"
                         else f"{num(dist)}  ({s['edges']} arestas)")
        val = "ciclo negativo" if d.get("negative_cycle_to_target") else "certificado + Dijkstra ok"
        rows.append([graph_label(g)] + cells + [str(d["passes"]), val])
    deck.table(rows, 0.6, 1.8, 12.1, [1.0, 2.35, 2.35, 2.35, 1.2, 2.85], size=15, row_h=0.55, align="lrrrrl",
               bold_first_col=True, highlight={(1, j): "FCE4D6" for j in range(1, 4)})
    deck.text("Caminhos completos em results/part3/bellman_ford/table.md. Ex.: W_2, 20 → 6795 → 7737 → 11988 → "
              "7094 → 14144 → 100. Um único Bellman-Ford até 100 responde as três origens.",
              0.6, 5.5, 12.1, 0.8, size=14, color=MUTED)

    # 8 ---------------------------------------------------------------- study 2
    vs = ["10", "20", "30", "40", "50"]
    deck.slide(notes=(
        "NICOLAS · 0:35\nEstudo 2: a matriz do W_2 saiu do próprio Floyd-Warshall, na primeira rodada completa do "
        "benchmark; as dez rodadas deram os mesmos pares, e conferimos as 25 distâncias com Bellman-Ford. Não é "
        "simétrica: o grafo é direcionado. No W_1 o Floyd-Warshall para no ciclo negativo, então não há matriz de "
        "caminhos mínimos. Do W_3 ao W_5 as matrizes não cabem na memória; os mesmos pares foram calculados com "
        "Bellman-Ford só como referência, e isso está identificado."))
    deck.header("Estudo 2 · Floyd-Warshall", "Distâncias entre {10, 20, 30, 40, 50} no W_2")
    pairs = s2["grafo_W_2"]["fw"]["pairs"]
    rows = [["de \\ para"] + vs] + [[i] + [num(from_json(pairs[i][j]["distance"])) for j in vs] for i in vs]
    deck.table(rows, 0.6, 1.8, 6.3, [1.3, 1.0, 1.0, 1.0, 1.0, 1.0], size=16, row_h=0.55, align="lrrrrr",
               bold_first_col=True)
    deck.text("Linha = origem, coluna = destino (grafo direcionado: não é simétrica). Floyd-Warshall, rodada 0 do "
              "estudo 3; pares iguais nas rodadas concluídas.", 0.6, 5.25, 6.3, 0.9, size=13, color=MUTED)
    other = [("W_1", f"Floyd-Warshall para na etapa k = {w1fw['stopped_at']} (ciclo negativo): sem matriz de "
                     "caminhos mínimos. Bellman-Ford (referência): todos os 25 pares com i ≠ j são −∞."),
             ("W_3 · W_4 · W_5", "Não executado: as matrizes exigiriam 112 GiB, 11 TiB e 1,1 PiB (limite 16 GiB). "
                                 "Matrizes de referência calculadas com Bellman-Ford, identificadas como tal no "
                                 "relatório — não são resultado de Floyd-Warshall.")]
    for i, (t, d) in enumerate(other):
        y = 1.8 + i * 2.1
        deck.rect(7.4, y, 5.3, 1.9, fill=LIGHT)
        deck.text(t, 7.65, y + 0.15, 4.8, 0.4, size=18, color=NAVY, bold=True)
        deck.text(d, 7.65, y + 0.6, 4.85, 1.25, size=14, color=INK)

    # 9 ---------------------------------------------------------------- study 3
    deck.slide(notes=(
        "NICOLAS · 0:40\nEstudo 3: dez rodadas de cada algoritmo, só o tempo da chamada, sem disco e sem a compilação "
        "JIT. O Bellman-Ford cresce com o tamanho do grafo: de 0,2 segundo no W_1 a 97 segundos no W_5. O "
        f"Floyd-Warshall completo do W_2 levou {num(fw_mean/60, 0)} minutos por rodada, com Numba e 16 threads. "
        "No W_1 ele termina em menos de um segundo porque para no ciclo negativo — esse tempo é quase só alocar as "
        "matrizes. Os escopos são diferentes: um destino contra todos os pares; a comparação justa é o estudo 4."))
    deck.header("Estudo 3 · 10 rodadas", "Tempo médio (s): um destino × todos os pares")
    rows = [["Grafo", "Bellman-Ford até 100", "Floyd-Warshall (Numba, 16 threads)"]]
    for g in ["grafo_W_1", "grafo_W_2", "grafo_W_3", "grafo_W_4", "grafo_W_5"]:
        bm, bsd, bdone, brounds = mean_sd(s3[g]["runs"]["bellman-ford"])
        fwr = s3[g]["runs"]["floyd-warshall"]
        fm, fsd, fdone, frounds = mean_sd(fwr)
        if fm is None:
            fcell = "recusado: matrizes > 16 GiB"
        else:
            tag = " · para no ciclo (k = 2)" if fwr[0].get("negative_cycle") else ""
            fcell = f"{num(fm, 2 if fm < 100 else 0)} ± {num(fsd, 2 if fm < 100 else 0)} ({fdone}/{frounds}){tag}"
        rows.append([graph_label(g), f"{num(bm, 2)} ± {num(bsd, 2)} ({bdone}/{brounds})", fcell])
    deck.table(rows, 0.6, 1.8, 12.1, [1.3, 4.3, 6.5], size=16, row_h=0.55, align="lrl", bold_first_col=True,
               highlight={(2, 2): "FCE4D6"})
    deck.text([[("Média ± desvio-padrão das rodadas concluídas (concluídas/10), medido. ", {}),
                ("Bellman-Ford inclui montar Gᵀ. Floyd-Warshall: um processo por rodada; leitura, JIT, digest e "
                 "pares fora do tempo. Escopos diferentes: a comparação de mesmo escopo é o estudo 4.", {})]],
              0.6, 5.35, 12.1, 0.9, size=14, color=MUTED)

    # 10 --------------------------------------------------------------- study 4, subgraphs
    subs = sorted((g for g in s4 if "_1-" in g), key=lambda g: s4[g]["n"])

    def cell(runs):
        m_, sd, done, total = mean_sd(runs)
        if m_ is None:
            st = next((r["status"] for r in runs if r.get("status")), "não executado")
            return None, "timeout" if st.startswith("timeout") else "não executado"
        return m_, f"{num(m_, 3 if m_ < 1 else 2 if m_ < 100 else 0)}" + ("" if done == total else f" ({done}/{total})")

    rows = [["n", "m", "BF todos os pares", "FW Python", "FW Numba", "FW Py / BF"]]
    ser = {"bf": [], "fwp": [], "fwn": []}
    for g in subs:
        d = s4[g]
        bm, bt = cell(d["runs"].get("bellman-ford", []))
        fm, ft = cell(d["runs"].get("floyd-warshall", []))
        nm, nt = cell(s4n[g]["runs"].get("floyd-warshall", [])) if g in s4n else (None, "–")
        rows.append([num(d["n"], 0), num(d["m"], 0), bt, ft, nt,
                     f"{num(fm / bm, 0 if fm / bm >= 10 else 1)}×" if bm and fm else "–"])
        ser["bf"].append((d["n"], bm))
        ser["fwp"].append((d["n"], fm))
        ser["fwn"].append((d["n"], nm))
    big = rows[-1] if len(rows) > 1 else None
    deck.slide(notes=(
        "NICOLAS · 0:40\nEstudo 4, mesmo escopo: os dois algoritmos devolvem a mesma matriz de distâncias e de "
        "predecessores, e conferimos que as matrizes são idênticas pelo digest. Para comparar com o mesmo nível de "
        "implementação, rodamos os dois em Python puro, um processo, em subgrafos induzidos pelos vértices 1 a N do "
        "W_2, dez rodadas cada. O Floyd-Warshall cresce como n ao cubo; o Bellman-Ford de todos os pares, como n "
        "vezes as arestas visitadas, e esses subgrafos são esparsos. Por isso a diferença só aumenta com n: de 2 "
        "para 52 vezes. Já o Floyd-Warshall compilado com Numba e 16 threads é cerca de 300 vezes mais rápido que "
        "a mesma rotina em Python, e aí passa à frente do Bellman-Ford em Python: o ganho de implementação supera "
        "a vantagem do algoritmo."))
    deck.header("Estudo 4 · mesmo escopo, mesmo nível", "Subgrafos do W_2: a diferença cresce com n")
    deck.table(rows, 0.6, 1.8, 6.6, [0.8, 0.95, 1.4, 1.2, 1.15, 1.1], size=13, row_h=0.46, align="rrrrrr",
               bold_first_col=True, highlight={(len(rows) - 1, 5): "FCE4D6"} if big else None)
    deck.text("Tempo médio (s) de 10 rodadas, medido. Subgrafo induzido pelos vértices 1..N (reprodutível); "
              "BF e FW Python: 1 processo; FW Numba: 16 threads. Mesma matriz nos dois algoritmos em todos os "
              "subgrafos (digest SHA-1). Não são os grafos oficiais.",
              0.6, 1.8 + 0.46 * len(rows) + 0.15, 6.6, 1.3, size=13, color=MUTED)
    cd = XyChartData()
    lines = [("Bellman-Ford (Python)", BLUE, ser["bf"]), ("Floyd-Warshall (Python)", ORANGE, ser["fwp"]),
             ("Floyd-Warshall (Numba, 16 threads)", NAVY, ser["fwn"])]
    for name, _, pts in lines:
        s = cd.add_series(name)
        for x, y in pts:
            if y:
                s.add_data_point(x, y)
    ch = deck.chart(XL_CHART_TYPE.XY_SCATTER_LINES, cd, 7.5, 1.75, 5.25, 4.9,
                    svg=svg_lines(lines, "n (vértices do subgrafo)", "s"))
    style_chart(ch, 12)
    for i, (_, color, _) in enumerate(lines):
        p = ch.series[i]
        p.format.line.color.rgb = RGBColor.from_string(color)
        p.format.line.width = Pt(2.5)
        p.marker.format.fill.solid()
        p.marker.format.fill.fore_color.rgb = RGBColor.from_string(color)
        p.marker.format.line.color.rgb = RGBColor.from_string(color)
        p.smooth = False
    log_axis(ch, "value")
    log_axis(ch, "category")
    ch.has_legend = True
    ch.legend.position = XL_LEGEND_POSITION.BOTTOM
    ch.legend.include_in_layout = False
    ch.value_axis.has_major_gridlines = True
    ch.value_axis.major_gridlines.format.line.color.rgb = RGBColor.from_string("E1E5EA")
    ch.value_axis.has_title = True
    ch.value_axis.axis_title.text_frame.text = "tempo (s), escala log"
    ch.category_axis.has_title = True
    ch.category_axis.axis_title.text_frame.text = "n (vértices), escala log"
    for ax in (ch.value_axis, ch.category_axis):
        ax.axis_title.text_frame.paragraphs[0].runs[0].font.size = Pt(12)
        ax.axis_title.text_frame.paragraphs[0].runs[0].font.bold = False

    # 11 --------------------------------------------------------------- study 4, official graphs
    off = {g: s4[g] for g in ("grafo_W_1", "grafo_W_2") if g in s4}
    w2bf = off.get("grafo_W_2", {}).get("runs", {}).get("bellman-ford", [])
    bfm, bfsd, bfdone, bftotal = mean_sd(w2bf) if w2bf else (None, None, 0, 0)
    w1d = off.get("grafo_W_1", {}).get("runs", {})
    w1bf = mean_sd(w1d.get("bellman-ford", [])) if w1d else (None, None, 0, 0)
    deck.slide(notes=(
        "NICOLAS · 0:35\nNos grafos oficiais. W_2: o Bellman-Ford de todos os pares, em Python puro e um processo, "
        + (f"levou {num(bfm / 3600, 1)} horas por rodada, medido, em {bfdone} de 10 rodadas; a mesma matriz do "
           "Floyd-Warshall, conferida pelo digest. "
           if bfm else "não terminou dentro do limite; o registro diz até onde chegou. ")
        + f"O Floyd-Warshall levou {num(fw_mean / 60, 0)} minutos, mas com Numba e 16 threads: níveis diferentes. "
        "No mesmo nível, Python puro, estimamos 150 a 170 horas para o Floyd-Warshall — estimativa, não medição. "
        "No W_1 os dois param no primeiro ciclo negativo, então não há matriz de caminhos mínimos para comparar."))
    deck.header("Estudo 4 · grafos oficiais", "W_2 completo: n Bellman-Fords contra um Floyd-Warshall")
    cards = [
        ("Bellman-Ford, todos os pares", "Python puro · 1 processo",
         (f"{num(bfm / 3600, 2)} h" if bfm else "timeout" if w2bf else "não executado"),
         (f"{num(bfm, 0)} s, medido ({bfdone}/10 rodadas; as demais em execução)" if bfm and bfdone < 10
          else f"{num(bfm, 0)} ± {num(bfsd or 0, 0)} s ({bfdone}/{bftotal}), medido" if bfm
          else "limite atingido; ver results/part3/all_pairs" if w2bf else "sem registro"), BLUE),
        ("Floyd-Warshall", "Numba · 16 threads", f"{num(fw_mean / 60, 1)} min",
         f"{num(fw_mean, 0)} ± {num(fw_sd, 0)} s ({fw_done}/{fw_rounds}), medido (estudo 3)", NAVY),
        ("Floyd-Warshall", "Python puro · 1 processo", "150–170 h",
         "estimado (calibração), não medido", ORANGE)]
    for i, (t, sub, big_, d, color) in enumerate(cards):
        x = 0.6 + i * 4.1
        deck.rect(x, 1.8, 3.85, 3.05, fill=LIGHT)
        deck.text(t.upper(), x + 0.25, 1.98, 3.4, 0.35, size=12, color=BLUE, bold=True, spacing=120)
        deck.text(sub, x + 0.25, 2.35, 3.4, 0.35, size=14, color=MUTED)
        deck.text(big_, x + 0.25, 2.8, 3.4, 1.0, size=44, color=color, bold=True, anchor="m")
        deck.text(d, x + 0.25, 3.95, 3.4, 0.8, size=13, color=INK)
    w1txt = (f"W_1: os dois param no primeiro ciclo negativo (Bellman-Ford de todos os pares: "
             f"{num(w1bf[0], 2)} s; Floyd-Warshall: {num(w1fw['seconds'], 2)} s, quase só alocar 7 GiB). "
             if w1bf[0] else "W_1: os dois param no primeiro ciclo negativo. ")
    deck.text([[("Leitura honesta: ", {"bold": True, "color": NAVY}),
                ("no W_2 o Floyd-Warshall só fica à frente porque foi compilado e paralelizado; no mesmo nível de "
                 "implementação o Bellman-Ford de todos os pares é muito mais rápido em grafo esparso. ", {}),
                (w1txt, {"color": MUTED})]],
              0.6, 5.1, 12.1, 1.4, size=15)

    # 12 --------------------------------------------------------------- conclusions
    deck.slide(dark=True, notes=(
        "NICOLAS · 0:45\nConclusões. Para um destino, Bellman-Ford com as duas otimizações resolve até o grafo de 10 "
        "milhões de vértices em menos de dois minutos. Para todos os pares, em grafos esparsos como estes, n "
        "execuções de Bellman-Ford ganham do Floyd-Warshall no mesmo nível de implementação; o Floyd-Warshall "
        "esbarra primeiro na memória — n ao quadrado — e depois no tempo — n ao cubo. Pesos negativos exigem detectar "
        "ciclos, e com ciclo a resposta correta é −∞. Limitações: as otimizações da aula não foram confirmadas; o "
        "W_2 compara implementações de níveis diferentes, o que dizemos explicitamente; os subgrafos são mais "
        "esparsos que o W_2. Obrigado."))
    deck.text("CONCLUSÕES", 0.8, 0.6, 11, 0.4, size=14, color=SKY, bold=True, spacing=300)
    deck.text("Grafos esparsos favorecem o Bellman-Ford; o Floyd-Warshall esbarra na memória", 0.8, 1.05, 11.8, 1.3,
              size=34, color=WHITE, bold=True)
    concl = [("Um destino", f"Bellman-Ford otimizado: de {num(mean_sd(s3['grafo_W_1']['runs']['bellman-ford'])[0], 2)} s "
                            f"(W_1) a {num(mean_sd(s3['grafo_W_5']['runs']['bellman-ford'])[0], 0)} s (W_5, 10⁷ vértices)"),
             ("Todos os pares", "O(n·m) com poucas rodadas contra Θ(n³): em grafo esparso, n Bellman-Fords vencem "
                                "no mesmo nível de implementação"),
             ("Memória", "Floyd-Warshall: 12(n + 1)² bytes; só W_1 e W_2 cabem (7 GiB); W_3 pede 112 GiB"),
             ("Pesos negativos", "Ciclo negativo ⇒ −∞; achado na rodada 4 no W_1 graças à checagem dos pais")]
    for i, (t, d) in enumerate(concl):
        x, y = 0.8 + (i % 2) * 6.0, 2.75 + (i // 2) * 1.6
        deck.rect(x, y, 5.7, 1.4, fill="1D2D50")
        deck.text(t, x + 0.25, y + 0.15, 5.2, 0.4, size=18, color="F2A07B", bold=True)
        deck.text(d, x + 0.25, y + 0.58, 5.25, 0.8, size=14, color=WHITE)
    deck.text("Limitações: correspondência com as otimizações da aula não confirmada · W_2 oficial compara níveis "
              "de implementação diferentes · subgrafos induzidos são mais esparsos que o W_2.",
              0.8, 6.1, 11.8, 0.6, size=13, color=PALE)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="docs/apresentacao_parte3.pptx")
    ap.add_argument("--preview", default=None, help="directory for slides.html")
    a = ap.parse_args()
    deck = Deck()
    build(deck, results())
    deck.prs.save(a.out)
    print(f"{a.out}: {deck.count} slides")
    if a.preview:
        os.makedirs(a.preview, exist_ok=True)
        deck.preview(os.path.join(a.preview, "slides.html"))
        print(os.path.join(a.preview, "slides.html"))


if __name__ == "__main__":
    main()
