"""Calibration of Floyd-Warshall on one graph: a short measured run plus the exact
amount of work, to estimate the time of a complete run before starting one.

Usage (from the repository root):
  python -m experiments.part3.fw_calibrate --graph grafo_W_2 [--data-dir ../T3] [--workers P]
                                           [--engine python|numpy|numba]
                                           [--budget 600] [--rounds 10] [--out results/part3/calibration]
Why not elapsed x n / k: stage k only processes the rows i with D[i][k] finite
at its start, i.e. the vertices i that reach k through intermediates in 1..k-1.
In a sparse graph there are few of them in the first stages, so the first
stages are much cheaper than the last ones.

What this script does:
  1. Exact work (not an estimate): rows(k) for every stage k, by a search in
     G^T from k that only expands vertices < k (the vertices it reaches are
     exactly the rows of stage k). Each row costs n + 1 cell comparisons.
  2. Measurement: FloydWarshall(workers=P).run on the graph, the real code,
     stopped after --budget seconds. Records the time of every stage and checks
     that the rows it processed match step 1.
  3. Estimate (labelled as such): the measured time plus, for each remaining
     stage, a + b x rows(k), with a and b fitted (least squares) on the last
     measured stages. The assumption is that the cost per row measured at the
     end of the calibration holds for the rest of the run.
Outputs: <out>/fw_<graph>_p<P>.json and .md (engine python), fw_<graph>_<engine>_p<P>.* (others)
"""
import argparse
import os
import statistics
import struct
import time
from array import array

from graphs import FloydWarshall

from ..common import environment, log, write_json
from ..memprobe import peak_rss
from .common import DEFAULT_DATA_DIR, DEFAULT_RESULTS, FW_ENGINES, default_workers, engine_versions, graph_path, load


class _Budget(Exception):
    pass


def stage_rows(rev, n, ks) -> array:
    """rows(k) for each k in ks: vertices reached from k in G^T expanding only vertices < k."""
    seen = array("i", [0]) * (n + 1)
    out = array("i")
    for k in ks:
        seen[k] = k
        stack, count = [k], 0
        while stack:
            for v in rev.neighbors(stack.pop()):
                if seen[v] != k:
                    seen[v] = k
                    count += 1
                    if v < k:
                        stack.append(v)
        out.append(count)
    return out


def exact_work(graph, workers) -> array:
    """rows(k), k = 1..n (index 0 unused), split among forked processes."""
    n = graph.n
    rev = graph.reversed()
    workers = max(1, min(workers, n)) if hasattr(os, "fork") else 1
    if workers == 1:
        return array("i", [0]) + stage_rows(rev, n, range(1, n + 1))
    children = []
    for w in range(workers):
        r, wfd = os.pipe()
        pid = os.fork()
        if pid == 0:
            code = 1
            try:
                os.close(r)
                data = stage_rows(rev, n, range(w + 1, n + 1, workers)).tobytes()
                view = memoryview(data)
                while view:
                    view = view[os.write(wfd, view):]
                code = 0
            finally:
                os._exit(code)
        os.close(wfd)
        children.append((pid, r, w))
    rows = array("i", [0]) * (n + 1)
    for pid, r, w in children:
        chunks = []
        while True:
            chunk = os.read(r, 1 << 20)
            if not chunk:
                break
            chunks.append(chunk)
        os.close(r)
        os.waitpid(pid, 0)
        part = array("i")
        part.frombytes(b"".join(chunks))
        rows[w + 1::workers] = part
    return rows


def fit(stages):
    """Least squares t = a + b * rows on (k, rows, seconds) stages."""
    xs = [r for _, r, _ in stages]
    ys = [t for _, _, t in stages]
    if len(set(xs)) < 2:
        return 0.0, sum(ys) / max(1, sum(xs))
    b, a = statistics.linear_regression(xs, ys)
    return max(a, 0.0), b


def calibrate(path, name, a) -> dict:
    g, load_s, _ = load(path, not a.undirected)
    n = g.n
    rec = {"graph": name, "n": n, "m": g.m, "workers": a.workers, "engine": a.engine,
           "engine_versions": engine_versions(a.engine), "budget_s": a.budget, "load_s": load_s,
           "matrix_gib": FloydWarshall.memory_bytes(n) / 2**30, "environment": environment()}
    log(f"{name}: counting the rows of every stage (exact)...")
    t = time.perf_counter()
    rows = exact_work(g, a.workers)
    rec["work_count_s"] = time.perf_counter() - t
    total_rows = sum(rows)
    rec.update(total_rows=total_rows, total_cells=total_rows * (n + 1),
               rows_fraction_of_dense=total_rows / (n * (n - 1)))
    log(f"{name}: {total_rows:,} rows ({rec['rows_fraction_of_dense']:.1%} of n(n-1)), "
        f"{rec['total_cells']:.3e} cells; counted in {rec['work_count_s']:.0f} s")

    stages = []
    t0 = None

    def on_stage(k, r):
        now = time.perf_counter()
        stages.append((k, r, now - on_stage.last))
        on_stage.last = now
        if now - t0 >= a.budget:
            raise _Budget()

    fw = FloydWarshall(max_vertices=None, workers=a.workers, on_stage=on_stage, engine=a.engine)
    fw.prepare()  # import / compile the engine outside the measurement
    log(f"{name}: Floyd-Warshall ({a.engine}) with {fw.workers} workers for {a.budget:.0f} s...")
    t0 = time.perf_counter()
    on_stage.last = t0
    finished = False
    with peak_rss(rec):
        try:
            result = fw.run(g)
            finished = True
        except _Budget:
            result = None
    elapsed = time.perf_counter() - t0
    k_done = stages[-1][0] if stages else 0
    done_rows = sum(r for _, r, _ in stages)
    mismatches = sum(1 for k, r, _ in stages if r != rows[k])
    rec["measured"] = {
        "elapsed_s": elapsed, "stages_done": k_done, "rows_done": done_rows,
        "work_fraction": done_rows / total_rows if total_rows else 1.0,
        "first_stage_s": stages[0][2] if stages else None,  # includes building the two matrices
        "rows_match_exact_count": mismatches == 0, "row_mismatches": mismatches,
        "finished": finished, "negative_cycle": bool(result and result.negative_cycle)}
    log(f"{name}: measured {elapsed:.0f} s, stages 1..{k_done}, {rec['measured']['work_fraction']:.3%} of the work; "
        f"rows match the exact count: {mismatches == 0}")
    if finished or not stages:
        return rec

    # cost model from the last measured stages: the last 30 % of the measured time, after stage 1
    tail, acc = [], 0.0
    for s in reversed(stages[1:]):
        tail.append(s)
        acc += s[2]
        if acc >= 0.3 * elapsed:
            break
    a0, b = fit(tail)
    remaining = sum(a0 + b * rows[k] for k in range(k_done + 1, n + 1))
    window_rows = sum(r for _, r, _ in tail)
    rec["model"] = {
        "window_stages": [tail[-1][0], tail[0][0]], "window_rows": window_rows,
        "seconds_per_stage": a0, "seconds_per_row": b, "ns_per_cell": b / (n + 1) * 1e9,
        "window_rows_per_stage": window_rows / len(tail)}
    total = elapsed + remaining
    rec["estimate"] = {"round_s": total, "round_h": total / 3600, "rounds": a.rounds,
                       "all_rounds_h": total * a.rounds / 3600, "remaining_s": remaining,
                       "kind": "estimate: measured time + fitted cost x exact remaining rows"}
    log(f"{name}: estimate {total / 3600:.1f} h per round, {total * a.rounds / 3600:.0f} h for {a.rounds} rounds "
        f"({b / (n + 1) * 1e9:.2f} ns per cell, engine {a.engine}, {fw.workers} workers)")
    return rec


def markdown(r) -> str:
    m = r["measured"]
    unit = "processos" if r.get("engine", "python") == "python" else "threads"
    lines = [f"# Calibração do Floyd-Warshall: {r['graph']}, engine {r.get('engine', 'python')} "
             f"({r['workers']} {unit})", "",
             f"- n = {r['n']:,}, m = {r['m']:,}; matrizes: {r['matrix_gib']:.2f} GiB; pico de RSS do processo "
             f"principal: {r.get('peak_rss_mb', 0) / 1024:.2f} GiB",
             f"- **Trabalho exato (contagem, não estimativa):** {r['total_rows']:,} linhas processadas no total "
             f"({r['rows_fraction_of_dense']:.1%} de n(n−1)), {r['total_cells']:.3e} células; "
             f"contado em {r['work_count_s']:.0f} s",
             f"- **Medido:** {m['elapsed_s']:.0f} s de execução real, etapas 1..{m['stages_done']:,} de "
             f"{r['n']:,}, {m['work_fraction']:.3%} do trabalho; linhas por etapa iguais à contagem exata: "
             f"{'sim' if m['rows_match_exact_count'] else 'NÃO'}"]
    if m["finished"]:
        lines.append("- A execução terminou dentro do orçamento"
                     + (f": parou no ciclo negativo após a etapa {m['stages_done']:,} (medido)."
                        if m["negative_cycle"] else " (medido); não há estimativa a fazer."))
    if "estimate" in r:
        md, e = r["model"], r["estimate"]
        lines += [f"- **Modelo de custo (ajustado nas etapas {md['window_stages'][0]}..{md['window_stages'][1]}, "
                  f"média de {md['window_rows_per_stage']:,.0f} linhas por etapa):** "
                  f"{md['ns_per_cell']:.2f} ns por célula, {md['seconds_per_stage'] * 1e3:.2f} ms fixos por etapa",
                  f"- **Estimativa (não é medição):** {e['round_h']:.1f} h por rodada; "
                  f"{e['all_rounds_h']:.0f} h ({e['all_rounds_h'] / 24:.1f} dias) para {e['rounds']} rodadas",
                  "", "Suposição: o custo por linha medido no fim da calibração vale para as etapas restantes."]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    ap.add_argument("--graph", default="grafo_W_2")
    ap.add_argument("--workers", type=int, default=default_workers(), help="processes per stage (1 = sequential)")
    ap.add_argument("--budget", type=float, default=600, help="seconds of measured Floyd-Warshall")
    ap.add_argument("--engine", choices=FW_ENGINES, default="python")
    ap.add_argument("--rounds", type=int, default=10, help="rounds of the official study, for the total")
    ap.add_argument("--undirected", action="store_true")
    ap.add_argument("--out", default=os.path.join(DEFAULT_RESULTS, "calibration"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    path = graph_path(a.data_dir, a.graph)
    name = os.path.splitext(os.path.basename(path))[0]
    rec = calibrate(path, name, a)
    engine = "" if a.engine == "python" else f"_{a.engine}"
    base = os.path.join(a.out, f"fw_{name}{engine}_p{a.workers}")
    write_json(base + ".json", rec)
    with open(base + ".md", "w", encoding="utf-8") as f:
        f.write(markdown(rec))
    log(f"done: {base}.md")


if __name__ == "__main__":
    main()
