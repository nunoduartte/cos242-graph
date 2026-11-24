"""Shared helpers for the Part 3 experiments (the generic ones come from experiments.common)."""
import hashlib
import math
import os
import time

from graphs import GraphReader

from ..common import log, rss_mb

PART3_GRAPHS = ["grafo_W_1", "grafo_W_2", "grafo_W_3", "grafo_W_4", "grafo_W_5"]
DEFAULT_DATA_DIR = os.environ.get("DATA_DIR_P3", "../T3")
DEFAULT_RESULTS = os.path.join("results", "part3")
INF = math.inf


def graph_path(data_dir: str, name: str) -> str:
    """<data_dir>/<name>.txt, or `name` itself when it is already a path to a file."""
    return name if os.path.isfile(name) else os.path.join(data_dir, f"{name}.txt")


def header_n(path: str) -> int:
    """Number of vertices from the first line, without reading the edges."""
    with open(path) as f:
        return int(f.readline())


def load(path: str, directed: bool, representation: str = "csr"):
    """Reads a weighted graph; returns (graph, seconds, MB added to RSS). Not timed as algorithm."""
    name = os.path.basename(path)
    log(f"{name}: loading ({os.path.getsize(path) / 2**20:.0f} MiB) as "
        f"{'directed' if directed else 'undirected'} {representation}...")
    base, t = rss_mb(), time.perf_counter()
    g = GraphReader.read(path, representation, weighted=True, directed=directed)
    seconds, memory = time.perf_counter() - t, rss_mb() - base
    log(f"{name}: n={g.n} m={g.m} min weight={g.min_weight} in {seconds:.1f} s, +{memory:.0f} MB")
    return g, seconds, memory


def jsonable(x: float):
    """inf / -inf / nan as strings, so the JSON files stay standard."""
    if isinstance(x, float) and not math.isfinite(x):
        return "inf" if x == INF else "-inf" if x == -INF else "nan"
    return x


def from_json(x):
    return {"inf": INF, "-inf": -INF}.get(x, x) if isinstance(x, str) else x


def fmt(d) -> str:
    """Distance for the tables: 2 decimals (the weights have 2), inf and -inf spelled out."""
    d = from_json(d)
    if d is None:
        return "-"
    if d == INF:
        return "∞ (inalcançável)"
    if d == -INF:
        return "−∞ (ciclo negativo)"
    return f"{d:.2f}".replace(".", ",")


def matrix_digest(rows, n: int) -> str:
    """SHA-1 of every distance rounded to 6 decimals (inputs have 2), so two algorithms
    that add the same weights in a different order still give the same digest."""
    h = hashlib.sha1()
    for i in range(1, n + 1):
        row = rows[i]
        row = row.tolist() if hasattr(row, "tolist") else row  # array, memoryview or NumPy row
        h.update(",".join("inf" if x == INF else f"{x:.6f}" for x in row[1:n + 1]).encode())
        h.update(b"\n")
    return h.hexdigest()


def cycle_info(graph, cycle):
    if not cycle:
        return None
    weight = sum(graph.weight(a, b) for a, b in zip(cycle, cycle[1:]))
    return {"edges": len(cycle) - 1, "weight": round(weight, 10), "vertices": cycle[:50]}


def per_graph(specs, value_type=float) -> dict:
    """["grafo_W_2=90000", ...] -> {"grafo_W_2": 90000.0}: per-graph overrides of a limit."""
    out = {}
    for spec in specs or []:
        name, sep, value = spec.partition("=")
        if not sep or not name:
            raise SystemExit(f"invalid per-graph value {spec!r}; expected NAME=VALUE")
        out[name] = value_type(value)
    return out


def default_workers() -> int:
    return os.cpu_count() or 1


FW_ENGINES = ("python", "numpy", "numba")

# Seconds a worker process may run beyond its algorithm timeout before it is killed: loading the
# graph and, after the timed call, the digest of the n x n matrix (~6 min at n = 25,000) and the pairs.
WORKER_GRACE_S = 1800


def engine_versions(engine: str) -> dict:
    """Versions of the optional packages an accelerated Floyd-Warshall engine used."""
    out = {}
    for mod in {"numpy": ["numpy"], "numba": ["numpy", "numba", "llvmlite"]}.get(engine, []):
        try:
            out[mod] = __import__(mod).__version__
        except ImportError:
            out[mod] = None
    return out


def benchmark_fw_runs(bench_dir: str, name: str):
    """Floyd-Warshall rounds of study 3 for a graph (None if there are none), so that
    studies 2 and 4 can use the same complete runs instead of repeating them."""
    import json
    path = os.path.join(bench_dir, f"{name}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    runs = data.get("runs", {}).get("floyd-warshall")
    return (runs, data.get("settings", {})) if runs else None


def run_rounds(runs, rounds, budget, one_round, save, label):
    """Runs one_round(i, limit) until `rounds` records exist in `runs` (resumable).

    A round that hits its time limit stops the remaining ones ("not run"), as
    does a refused run (the graph is above a size limit) and the end of the
    budget (seconds of runs for this graph and algorithm). save() is called after
    every round, so an interruption loses at most the round in progress.
    """
    from ..common import log
    spent = sum(r.get("seconds") or r.get("interrupted_after_s") or 0 for r in runs)
    while len(runs) < rounds:
        i = len(runs)
        blocked = next((r["status"] for r in runs if r["status"].startswith(("timeout", "refused", "não", "killed", "failed"))), None)
        longest = max((r["seconds"] for r in runs if r.get("seconds")), default=0)
        if blocked:
            rec = {"round": i, "status": f"not run (previous round: {blocked.split(':')[0]})", "seconds": None}
        elif budget and (spent >= budget or budget - spent < longest):
            rec = {"round": i, "status": "not run (budget)", "seconds": None}
        else:
            rec = {"round": i, **one_round(i, budget - spent if budget else None)}
            spent += rec.get("seconds") or rec.get("interrupted_after_s") or 0
        runs.append(rec)
        log(f"{label} round {i}: {rec['status']}" + (f" {rec['seconds']:.3f} s" if rec.get("seconds") else ""))
        save()
    return runs


def summarize_runs(runs) -> dict:
    """Mean, sample standard deviation, min and max of the finished rounds."""
    import statistics
    times = [r["seconds"] for r in runs if r.get("seconds") is not None]
    out = {"rounds": len(runs), "finished": len(times),
           "mean_s": statistics.fmean(times) if times else None,
           "stdev_s": statistics.stdev(times) if len(times) > 1 else None,
           "min_s": min(times) if times else None, "max_s": max(times) if times else None}
    stopped = [r for r in runs if r.get("seconds") is None]
    out["note"] = stopped[0]["status"] if stopped else ""
    outcomes = sorted({r["status"] for r in runs if r.get("seconds") is not None})
    out["outcome"] = ", ".join(outcomes)
    return out
