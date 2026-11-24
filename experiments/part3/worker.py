"""One all-pairs run (Floyd-Warshall or all-pairs Bellman-Ford) in its own process.

Started by the Part 3 studies through experiments.memprobe.run_worker, never by
hand. Loading the graph is not timed; only the algorithm call is (perf_counter,
garbage collector paused). The record is printed as one JSON line:
  status       ok | negative cycle | timeout (> T s) | refused: <reason>
  seconds      time of the call (None unless it finished)
  progress     how far an interrupted run got: stage k (FW) or sources done (BF)
  rows_done    FW only: rows processed in the finished stages (n + 1 cells each)
  workers      FW only: processes (engine python) or threads (numpy, numba) per stage
  engine       FW only: python | numpy | numba, with the package versions
  pairs        D[i][j] for the requested vertices, with the paths
  digest       SHA-1 of the whole distance matrix (to compare the two algorithms)
  peak_*       RSS of the call (kernel high-water mark), see experiments.memprobe
"""
import argparse
import gc
import sys
import time

from graphs import BellmanFord, FloydWarshall, GraphTooLargeError

from ..common import RunTimeout, time_limit
from ..memprobe import clean_baseline, emit, peak_rss
from .common import FW_ENGINES, cycle_info, engine_versions, jsonable, load, matrix_digest

ALGORITHMS = {"fw": "Floyd-Warshall", "bf-all": "Bellman-Ford (todos os pares)"}


def run(a) -> dict:
    g, load_s, _ = load(a.graph, a.directed, a.representation)
    rec = {"algorithm": a.algorithm, "n": g.n, "m": g.m, "load_s": load_s, "seconds": None,
           "baseline_rss_mb": clean_baseline()}
    if a.algorithm == "fw":
        algo = FloydWarshall(max_vertices=a.max_vertices or None, workers=a.workers, engine=a.engine)
        try:
            algo.prepare()  # import / compile the engine before the timed call
        except ImportError as e:
            rec["status"] = f"failed: {e}"
            return rec
        rec.update(workers=algo.workers, engine=a.engine, engine_versions=engine_versions(a.engine))
        call, progress = (lambda: algo.run(g)), (lambda: algo.stage)
    else:
        algo = BellmanFord()
        call, progress = (lambda: algo.all_pairs(g, max_vertices=a.max_vertices or None)), \
            (lambda: algo.sources_done)
    if any(v > g.n for v in a.pairs):
        rec["status"] = f"refused: --pairs has a vertex above n = {g.n}"
        return rec
    result = None
    gc.collect()
    gc.disable()
    t = time.perf_counter()
    try:
        with peak_rss(rec), time_limit(a.timeout or None):
            result = call()
        rec["seconds"] = time.perf_counter() - t
    except RunTimeout:
        rec["status"] = f"timeout (> {a.timeout:.0f} s)"
        rec["interrupted_after_s"] = time.perf_counter() - t
    except GraphTooLargeError as e:
        rec["status"] = f"refused: {e}"
    finally:
        gc.enable()
    rec["progress"] = progress()
    if a.algorithm == "fw":
        rec["rows_done"] = algo.rows_done
    if result is None:
        return rec
    if result.negative_cycle is not None:
        rec["status"] = "negative cycle"
        rec["negative_cycle"] = cycle_info(g, result.negative_cycle)
        rec["stopped_at"] = result.stopped_at
        return rec
    rec["status"] = "ok"
    if a.digest:
        rec["digest"] = matrix_digest(result.dist, g.n)
    if a.pairs:
        rec["pairs"] = {str(i): {str(j): {"distance": jsonable(result.distance(i, j)), "path": result.path(i, j)}
                                 for j in a.pairs} for i in a.pairs}
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--worker", action="store_true", required=True)
    ap.add_argument("--graph", required=True, help="path of the graph file")
    ap.add_argument("--algorithm", choices=sorted(ALGORITHMS), required=True)
    ap.add_argument("--directed", type=int, default=1)
    ap.add_argument("--representation", default="csr")
    ap.add_argument("--max-vertices", type=int, default=0, help="size limit of the algorithm; 0 = none")
    ap.add_argument("--timeout", type=float, default=0, help="seconds; 0 = none")
    ap.add_argument("--pairs", type=int, nargs="*", default=[])
    ap.add_argument("--digest", type=int, default=0)
    ap.add_argument("--workers", type=int, default=1, help="FW: processes/threads per stage (1 = sequential)")
    ap.add_argument("--engine", choices=FW_ENGINES, default="python", help="FW: row loop implementation")
    a = ap.parse_args()
    if any(v < 1 for v in a.pairs):
        sys.exit("invalid --pairs")
    emit(run(a))


if __name__ == "__main__":
    main()
