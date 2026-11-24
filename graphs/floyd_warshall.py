"""Floyd-Warshall: all-pairs shortest paths with negative weights.

Recurrence: D_k[i][j] = min(D_{k-1}[i][j], D_{k-1}[i][k] + D_{k-1}[k][j]), the
lightest i -> j path whose intermediate vertices are all in 1..k.

Memory optimization: a single n x n matrix updated in place instead of one
matrix per k (n^3 cells) or two alternating ones. It is safe because stage k
does not change row k or column k when D[k][k] = 0:
D[k][j] = min(D[k][j], D[k][k] + D[k][j]) and D[i][k] = min(D[i][k], D[i][k] + D[k][k]).
So reading D[i][k] and D[k][j] during stage k gives the D_{k-1} values. Storage:
distances in array('d') rows (8 bytes per cell) and predecessors in array('i')
rows (4 bytes), 12 (n+1)^2 bytes in all, instead of 24+ bytes per cell for
Python lists of floats.

pred[i][j] is the vertex before j on a shortest i -> j path, so row i is the
tree of shortest paths from i (the same convention as Dijkstra's `parent`).

A negative cycle shows up as D[i][i] < 0. The run stops at the first one: the
distances are then undefined for some pairs, and an exact answer for the others
would need all n stages, which the official graphs cannot afford.

Parallel stages (workers > 1): within stage k the rows i are independent. Row i
only reads itself and row k, and row k does not change in stage k. So the rows
can be split among processes (fork, Linux/Unix) that share the two matrices
through anonymous shared memory (mmap), with a barrier between stages. Every
cell gets the same operations in the same order of k as in the sequential run,
so the matrices are bit-for-bit identical. With a negative cycle at stage k,
the run reports the smallest i with D[i][i] < 0, the same row (and so the same
cycle) where the sequential loop stops.

Accelerated engines (engine="numpy" or "numba", optional dependencies, see
graphs/floyd_warshall_engines.py): the same stage loop, with the matrices in two
NumPy arrays and the row loop of each stage in NumPy ufuncs or in code compiled
by Numba. Same comparisons, same additions, same order of k: same matrices.
"""
import mmap
import os
import struct
from array import array
from dataclasses import dataclass
from itertools import compress, repeat
from operator import add, gt
from typing import Callable, List, Optional, Sequence

from .bellman_ford import NegativeCycleError
from .shortest_paths import ShortestPaths

INF = float("inf")


class GraphTooLargeError(ValueError):
    """The graph is above the configured size limit for an O(n^2)-memory, O(n^3)-time algorithm."""


@dataclass
class AllPairsShortestPaths:
    n: int
    dist: Sequence      # dist[i][j], rows and columns 1..n (index 0 unused); rows are
                        # array('d') or, in a parallel run, memoryviews of shared memory
    pred: Sequence      # pred[i][j]: vertex before j on a shortest i -> j path; 0 if i == j, -1 if none
    negative_cycle: Optional[List[int]] = None  # closed list [c0, c1, ..., c0] in edge order
    stopped_at: Optional[int] = None  # Floyd-Warshall: stage k of the negative cycle;
                                      # all-pairs Bellman-Ford: the source being processed

    def _require_no_cycle(self):
        if self.negative_cycle is not None:
            raise NegativeCycleError(self.negative_cycle)

    def distance(self, u: int, v: int) -> float:
        self._require_no_cycle()
        return float(self.dist[u][v])

    def path(self, u: int, v: int) -> Optional[List[int]]:
        """Vertices from u to v, both included; None if v is unreachable from u."""
        self._require_no_cycle()
        return self.tree(u).path_to(v)

    def tree(self, u: int) -> ShortestPaths:
        """Shortest-path tree from u (Dijkstra's result type)."""
        self._require_no_cycle()
        return ShortestPaths(u, _as_list(self.dist[u]), _as_list(self.pred[u]))


class FloydWarshall:
    name = "Floyd-Warshall"

    def __init__(self, max_vertices: Optional[int] = 3000, max_memory_bytes: Optional[int] = None,
                 workers: int = 1, on_stage: Optional[Callable[[int, int], None]] = None,
                 engine: str = "python"):
        """Refuses graphs with more than `max_vertices` vertices or whose two
        matrices need more than `max_memory_bytes` (None = no limit). At about
        30-60 ns per cell update in CPython, n = 3000 is already ~15-30 min.
        workers > 1 splits the rows of each stage among that many processes.
        on_stage(k, rows) is called after each stage k, with the number of rows
        it processed (rows i with D[i][k] finite); for progress and calibration.
        engine: "python" (default, standard library only; workers = processes),
        "numpy" or "numba" (optional dependencies; workers = threads)."""
        if engine not in ENGINES:
            raise ValueError(f"engine must be one of {ENGINES}, not {engine!r}")
        self.engine = engine
        self.max_vertices = max_vertices
        self.max_memory_bytes = max_memory_bytes
        self.workers = max(1, workers)
        self.on_stage = on_stage
        self.stage = 0  # last stage k started; lets a caller that interrupts the run see how far it got
        self.rows_done = 0  # rows processed in the finished stages (each costs n + 1 cell comparisons)

    def prepare(self) -> None:
        """Imports (and, for Numba, compiles) the engine now, so that a timed run()
        does not include it. run() does it by itself when this was not called."""
        if self.engine != "python":
            from . import floyd_warshall_engines as engines
            engines.require_numpy()
            if self.engine == "numba":
                engines._numba_kernel()

    @staticmethod
    def memory_bytes(n: int) -> int:
        """Payload of the two matrices: 8 + 4 bytes per cell, (n+1)^2 cells."""
        return 12 * (n + 1) ** 2

    def check_size(self, n: int) -> None:
        if self.max_vertices is not None and n > self.max_vertices:
            raise GraphTooLargeError(
                f"Floyd-Warshall on n = {n} vertices: n^3 = {n ** 3:.2e} cell updates and "
                f"{self.memory_bytes(n) / 2**30:.1f} GiB; the limit is {self.max_vertices} vertices")
        if self.max_memory_bytes is not None and self.memory_bytes(n) > self.max_memory_bytes:
            raise GraphTooLargeError(
                f"Floyd-Warshall on n = {n} vertices needs {self.memory_bytes(n) / 2**30:.1f} GiB "
                f"for its matrices; the limit is {self.max_memory_bytes / 2**30:.1f} GiB")

    def run(self, graph) -> AllPairsShortestPaths:
        n = graph.n
        self.check_size(n)
        self.stage = self.rows_done = 0
        if self.engine != "python":
            return self._run_engine(graph)
        if self.workers > 1 and n > 1 and hasattr(os, "fork"):
            dist, pred = _shared_matrices(n)
        else:
            dist = [array("d", [INF]) * (n + 1) for _ in range(n + 1)]
            pred = [array("i", [-1]) * (n + 1) for _ in range(n + 1)]
        for u in graph.vertices():
            du, pu = dist[u], pred[u]
            du[u], pu[u] = 0.0, 0
            for v, w in graph.weighted_neighbors(u):
                if w < du[v]:  # a parallel edge keeps the lightest weight; a loop only if negative
                    du[v], pu[v] = w, u
            if du[u] < 0:  # negative self-loop
                return self._negative_cycle(graph, dist, pred, u, 0)
        if isinstance(dist[0], memoryview):
            return self._run_parallel(graph, dist, pred)
        columns = range(n + 1)
        for k in range(1, n + 1):
            self.stage = k
            dk, pk = dist[k], pred[k]
            rows = 0
            for i in range(1, n + 1):
                di = dist[i]
                dik = di[k]
                if dik == INF or i == k:  # nothing to gain through k; row k does not change
                    continue
                rows += 1
                pi = pred[i]
                # j where D[i][k] + D[k][j] < D[i][j], found at C speed; only those are updated
                for j in compress(columns, map(gt, di, map(add, repeat(dik), dk))):
                    di[j] = dik + dk[j]
                    pi[j] = pk[j]
                if di[i] < 0:
                    return self._negative_cycle(graph, dist, pred, i, k)
            self.rows_done += rows
            if self.on_stage:
                self.on_stage(k, rows)
        return AllPairsShortestPaths(n, dist, pred)

    def _run_engine(self, graph) -> AllPairsShortestPaths:
        """The same stages with an accelerated row loop (graphs/floyd_warshall_engines.py)."""
        from . import floyd_warshall_engines as engines
        n = graph.n
        stage = engines.make_stage(self.engine, n, self.workers)  # Numba compiles here, once
        try:
            dist, pred = engines.allocate(n)
            for u in graph.vertices():
                du, pu = dist[u], pred[u]
                du[u], pu[u] = 0.0, 0
                for v, w in graph.weighted_neighbors(u):
                    if w < du[v]:
                        du[v], pu[v] = w, u
                if du[u] < 0:
                    return self._negative_cycle(graph, dist, pred, u, 0)
            for k in range(1, n + 1):
                self.stage = k
                rows, negative = stage(dist, pred, k)
                if negative:
                    return self._negative_cycle(graph, dist, pred, negative, k)
                self.rows_done += rows
                if self.on_stage:
                    self.on_stage(k, rows)
            return AllPairsShortestPaths(n, dist, pred)
        finally:
            stage.close()

    def _run_parallel(self, graph, dist, pred) -> AllPairsShortestPaths:
        """The same stages, with the rows of each stage split among forked processes."""
        n = graph.n
        workers = min(self.workers, n)
        children = []  # (pid, to_child, from_child)
        try:
            for w in range(workers):
                down_r, down_w = os.pipe()
                up_r, up_w = os.pipe()
                pid = os.fork()
                if pid == 0:  # child: rows i = w+1, w+1+workers, ...
                    code = 1
                    try:
                        os.close(down_w)
                        os.close(up_r)
                        for _, d, u in children:  # pipes of the earlier children are not ours
                            os.close(d)
                            os.close(u)
                        _stage_worker(n, dist, pred, range(w + 1, n + 1, workers), down_r, up_w)
                        code = 0
                    finally:
                        os._exit(code)
                os.close(down_r)
                os.close(up_w)
                children.append((pid, down_w, up_r))
            for k in range(1, n + 1):
                self.stage = k
                order = struct.pack("i", k)
                for _, down, _ in children:
                    os.write(down, order)
                rows, negative = 0, []
                for _, _, up in children:
                    reply = _read_exactly(up, 8)
                    r, neg = struct.unpack("ii", reply)
                    rows += r
                    if neg:
                        negative.append(neg)
                if negative:  # the smallest row: the one where the sequential loop stops
                    return self._negative_cycle(graph, dist, pred, min(negative), k)
                self.rows_done += rows
                if self.on_stage:
                    self.on_stage(k, rows)
            return AllPairsShortestPaths(n, dist, pred)
        finally:
            for pid, down, up in children:
                for fd in (down, up):
                    try:
                        os.close(fd)
                    except OSError:
                        pass
                try:  # an interrupted run (timeout) must not leave children computing
                    os.kill(pid, 9)
                except ProcessLookupError:
                    pass
                os.waitpid(pid, 0)

    @staticmethod
    def _negative_cycle(graph, dist, pred, i, k) -> AllPairsShortestPaths:
        """D[i][i] < 0: the predecessors of row i give a closed walk i -> ... -> i
        of negative weight; it is split into simple cycles and a negative one kept."""
        walk, v = [i], int(pred[i][i])
        while v != i and v > 0 and len(walk) <= graph.n:
            walk.append(v)
            v = int(pred[i][v])
        walk.append(i)
        walk.reverse()  # predecessors were followed backwards: now in edge order
        cycle = _negative_simple_cycle(graph, walk)
        if cycle is None:  # defensive: the walk was not a valid closed walk
            from .bellman_ford import BellmanFord
            cycle = BellmanFord().find_negative_cycle(graph)
        return AllPairsShortestPaths(graph.n, dist, pred, cycle, k)


ENGINES = ("python", "numpy", "numba")


def _as_list(row) -> list:
    """A row as a list of Python numbers (array, memoryview or NumPy row)."""
    return row.tolist() if hasattr(row, "tolist") and not isinstance(row, array) else list(row)


def _shared_matrices(n):
    """Distance and predecessor matrices in anonymous shared memory (inherited by
    forked processes), as lists of row memoryviews: dist[i][j], pred[i][j]."""
    size = n + 1
    dmem = memoryview(mmap.mmap(-1, 8 * size * size)).cast("d")
    pmem = memoryview(mmap.mmap(-1, 4 * size * size)).cast("i")
    inf_row, none_row = array("d", [INF]) * size, array("i", [-1]) * size
    dist, pred = [], []
    for i in range(size):
        d, p = dmem[i * size:(i + 1) * size], pmem[i * size:(i + 1) * size]
        d[:], p[:] = inf_row, none_row
        dist.append(d)
        pred.append(p)
    return dist, pred


def _read_exactly(fd, count) -> bytes:
    data = b""
    while len(data) < count:
        chunk = os.read(fd, count - len(data))
        if not chunk:
            raise RuntimeError("Floyd-Warshall worker process ended unexpectedly")
        data += chunk
    return data


def _stage_worker(n, dist, pred, my_rows, down, up):
    """Child process: for each stage k sent by the parent, the sequential row loop
    over its own rows; replies (rows processed, first row with D[i][i] < 0 or 0)."""
    columns = range(n + 1)
    while True:
        order = os.read(down, 4)
        if len(order) < 4:  # the parent closed the pipe (end, or the parent died)
            return
        k = struct.unpack("i", order)[0]
        dk, pk = dist[k], pred[k]
        rows = negative = 0
        for i in my_rows:
            di = dist[i]
            dik = di[k]
            if dik == INF or i == k:
                continue
            rows += 1
            pi = pred[i]
            for j in compress(columns, map(gt, di, map(add, repeat(dik), dk))):
                di[j] = dik + dk[j]
                pi[j] = pk[j]
            if di[i] < 0:
                negative = i
                break
        os.write(up, struct.pack("ii", rows, negative))


def _negative_simple_cycle(graph, walk) -> Optional[List[int]]:
    """Splits a closed walk into simple cycles; returns the first of negative weight."""
    stack, where = [], {}
    for v in walk:
        if v in where:  # close the cycle that starts at the earlier visit of v
            start = where[v]
            cycle = stack[start:] + [v]
            weights = [graph.weight(a, b) for a, b in zip(cycle, cycle[1:])]
            if None in weights:
                return None
            if sum(weights) < 0:
                return cycle
            for u in stack[start + 1:]:
                del where[u]
            del stack[start + 1:]
        else:
            where[v] = len(stack)
            stack.append(v)
    return None
