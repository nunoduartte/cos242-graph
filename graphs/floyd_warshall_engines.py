"""Optional accelerated kernels for one Floyd-Warshall stage (NumPy or Numba).

The library itself needs only the standard library: these engines are used only
when FloydWarshall(engine="numpy" | "numba") is asked for, and the import error
says what is missing. Both keep the semantics of the sequential loop in
graphs/floyd_warshall.py exactly:

  for i with D[i][k] finite and i != k, for every column j:
      if D[i][j] > D[i][k] + D[k][j]:  D[i][j] = D[i][k] + D[k][j];  P[i][j] = P[k][j]

- the same IEEE-754 double addition and the same strict comparison, so the
  same cells change, to the same values (no fast-math, no reassociation);
- the same order of the stages k = 1..n (no blocked / tiled variant: those
  change the order in which the candidates are tried, and so possibly which of
  two equal-weight predecessors is kept);
- rows of one stage are independent (row k does not change in stage k), so
  splitting them among threads does not change any cell;
- after stage k, the smallest i with D[i][i] < 0 is reported, the row where
  the sequential loop stops.

Matrices: one (n+1) x (n+1) float64 array for the distances and one int32 array
for the predecessors, 12 (n+1)^2 bytes, the same as the pure Python version.
"""
import math

INF = math.inf


def require_numpy():
    try:
        import numpy
    except ImportError as e:  # pragma: no cover - depends on the environment
        raise ImportError("FloydWarshall(engine='numpy' or 'numba') needs NumPy (pip install numpy); "
                          "the default engine='python' needs nothing") from e
    return numpy


def allocate(n):
    np = require_numpy()
    dist = np.full((n + 1, n + 1), INF, dtype=np.float64)
    pred = np.full((n + 1, n + 1), -1, dtype=np.int32)
    return dist, pred


class NumpyStage:
    """Stage k with NumPy ufuncs over blocks of contiguous rows (views, in place).

    Rows with D[i][k] = inf go through the same ufuncs but cannot change
    (inf + x = inf is never < D[i][j]); a block where every D[i][k] is inf is
    skipped. With workers > 1 the blocks run in a thread pool (the ufuncs
    release the GIL). Temporary memory: workers x block_rows x (n+1) x 9 bytes."""

    def __init__(self, n, workers=1, block_rows=256):
        np = require_numpy()
        self.np, self.n = np, n
        self.workers = max(1, workers)
        self.block_rows = block_rows
        self.blocks = [(a, min(n + 1, a + block_rows)) for a in range(1, n + 1, block_rows)]
        self.pool = None
        if self.workers > 1:
            from concurrent.futures import ThreadPoolExecutor
            self.pool = ThreadPoolExecutor(self.workers)
        self.local = __import__("threading").local()

    def _buffers(self):
        np = self.np
        if not hasattr(self.local, "cand"):
            self.local.cand = np.empty((self.block_rows, self.n + 1), np.float64)
            self.local.mask = np.empty((self.block_rows, self.n + 1), np.bool_)
        return self.local.cand, self.local.mask

    def _block(self, dist, pred, col, dk, pk, a, b):
        np = self.np
        cik = col[a:b]
        if not np.isfinite(cik).any():
            return
        cand, mask = self._buffers()
        cand, mask = cand[:b - a], mask[:b - a]
        np.add(cik[:, None], dk, out=cand)
        block = dist[a:b]
        np.greater(block, cand, out=mask)
        np.copyto(block, cand, where=mask)
        np.copyto(pred[a:b], pk, where=mask)

    def __call__(self, dist, pred, k):
        """Runs stage k; returns (rows processed, smallest i with D[i][i] < 0 or 0)."""
        np = self.np
        col = dist[:, k].copy()  # column k does not change in stage k; copied so blocks can't alias it
        dk, pk = dist[k].copy(), pred[k].copy()
        rows = int(np.count_nonzero(col[1:] != INF)) - 1  # row k itself (D[k][k] = 0) is not processed
        if self.pool:
            list(self.pool.map(lambda ab: self._block(dist, pred, col, dk, pk, *ab), self.blocks))
        else:
            for a, b in self.blocks:
                self._block(dist, pred, col, dk, pk, a, b)
        negative = np.flatnonzero(np.diagonal(dist)[1:] < 0)
        return rows, int(negative[0]) + 1 if negative.size else 0

    def close(self):
        if self.pool:
            self.pool.shutdown()


_NUMBA_KERNEL = None


def _numba_kernel():
    global _NUMBA_KERNEL
    if _NUMBA_KERNEL is None:
        require_numpy()
        try:
            import numba
        except ImportError as e:  # pragma: no cover - depends on the environment
            raise ImportError("FloydWarshall(engine='numba') needs Numba (pip install numba)") from e
        from numba import prange

        # compiled once here, before any timed run (explicit signature = eager compilation)
        @numba.njit("void(float64[:, ::1], int32[:, ::1], int64, int8[::1])", parallel=True, cache=False)
        def stage(dist, pred, k, flags):
            size = dist.shape[0]
            for i in prange(1, size):
                flags[i] = 0
                dik = dist[i, k]
                if i == k or dik == math.inf:
                    continue
                flags[i] = 1
                for j in range(size):
                    c = dik + dist[k, j]
                    if dist[i, j] > c:
                        dist[i, j] = c
                        pred[i, j] = pred[k, j]
                if dist[i, i] < 0:
                    flags[i] = 2
        _NUMBA_KERNEL = stage
    return _NUMBA_KERNEL


class NumbaStage:
    """Stage k compiled by Numba: the sequential row loop, rows split among
    `workers` threads (prange). Extra memory: one byte per row."""

    def __init__(self, n, workers=1):
        np = require_numpy()
        import numba
        self.np = np
        self.kernel = _numba_kernel()
        self.workers = max(1, min(workers, numba.config.NUMBA_NUM_THREADS))
        numba.set_num_threads(self.workers)
        self.flags = np.zeros(n + 1, np.int8)

    def __call__(self, dist, pred, k):
        np = self.np
        self.kernel(dist, pred, k, self.flags)
        rows = int(np.count_nonzero(self.flags))
        negative = np.flatnonzero(self.flags == 2)
        return rows, int(negative[0]) if negative.size else 0

    def close(self):
        pass


def make_stage(engine, n, workers):
    if engine == "numpy":
        return NumpyStage(n, workers)
    if engine == "numba":
        return NumbaStage(n, workers)
    raise ValueError(f"unknown Floyd-Warshall engine {engine!r}")
