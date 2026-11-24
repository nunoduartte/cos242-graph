"""Graph representations (Strategy pattern for edge storage).

Every representation can store edge weights. An unweighted representation
reports weight 1.0 for every edge, so weighted algorithms also run on the
graphs of Part 1.

A directed representation stores only u -> v for add_edge(u, v): neighbors(u)
are then the out-neighbors of u and degree(u) is the out-degree. An undirected
one stores both directions, as in Parts 1 and 2.
"""
from abc import ABC, abstractmethod
from array import array
from bisect import bisect_left
from itertools import accumulate, repeat
from typing import Iterable, Optional, Tuple

INF = float("inf")


class Representation(ABC):
    """Common contract for the data structures that store adjacency."""

    def __init__(self, n: int, weighted: bool = False, directed: bool = False):
        self.n = n
        self.weighted = weighted
        self.directed = directed

    @abstractmethod
    def add_edge(self, u: int, v: int, w: float = 1.0) -> bool:
        """Insert u -> v (and v -> u if undirected) with weight w; return True if
        the edge was actually added."""

    @abstractmethod
    def neighbors(self, u: int) -> Iterable[int]:
        ...

    def weighted_neighbors(self, u: int) -> Iterable[Tuple[int, float]]:
        """(v, weight) pairs; weight 1.0 when the graph has no weights."""
        return zip(self.neighbors(u), repeat(1.0))

    @abstractmethod
    def weight(self, u: int, v: int) -> Optional[float]:
        """Weight of {u, v}, or None if there is no such edge."""

    @abstractmethod
    def degree(self, u: int) -> int:
        ...

    def finalize(self) -> int:
        """Called after loading; returns how many duplicate edges were dropped."""
        return 0

    def transposed(self) -> Optional["Representation"]:
        """The same edges reversed, built directly; None = no fast path (Graph.reversed
        then re-adds every edge)."""
        return None


class AdjacencyList(Representation):
    """O(n + m) memory. Repeated edges are removed in finalize() (sort + unique);
    for weighted graphs the lightest copy of a repeated edge is kept."""

    def __init__(self, n: int, weighted: bool = False, directed: bool = False):
        super().__init__(n, weighted, directed)
        self._adj = [array("i") for _ in range(n + 1)]
        self._w = [array("d") for _ in range(n + 1)] if weighted else None

    def add_edge(self, u, v, w=1.0):
        self._adj[u].append(v)
        if self._w is not None:
            self._w[u].append(w)
        if not self.directed:
            self._adj[v].append(u)
            if self._w is not None:
                self._w[v].append(w)
        return True

    def neighbors(self, u):
        return self._adj[u]

    def weighted_neighbors(self, u):
        if self._w is None:
            return super().weighted_neighbors(u)
        return zip(self._adj[u], self._w[u])

    def weight(self, u, v):
        row = self._adj[u]
        i = bisect_left(row, v)  # rows are sorted by finalize()
        if i == len(row) or row[i] != v:
            return None
        return self._w[u][i] if self._w is not None else 1.0

    def degree(self, u):
        return len(self._adj[u])

    def finalize(self):
        removed = 0
        for u in range(1, self.n + 1):
            if self._w is None:
                unique = array("i", sorted(set(self._adj[u])))
            else:
                best = {}
                for v, w in zip(self._adj[u], self._w[u]):
                    if w < best.get(v, INF):
                        best[v] = w
                unique = array("i", sorted(best))
                self._w[u] = array("d", (best[v] for v in unique))
            removed += len(self._adj[u]) - len(unique)
            self._adj[u] = unique
        return removed if self.directed else removed // 2


class AdjacencyMatrix(Representation):
    """O(n^2) memory: one byte per cell (+ 8 bytes per cell when weighted).
    Repeated edges keep the lightest weight."""

    def __init__(self, n: int, weighted: bool = False, directed: bool = False):
        super().__init__(n, weighted, directed)
        self._adj = [bytearray(n + 1) for _ in range(n + 1)]
        self._w = [array("d", bytes(8 * (n + 1))) for _ in range(n + 1)] if weighted else None

    def add_edge(self, u, v, w=1.0):
        if self._adj[u][v]:
            if self._w is not None and w < self._w[u][v]:
                self._set_weight(u, v, w)
            return False
        self._adj[u][v] = 1
        if not self.directed:
            self._adj[v][u] = 1
        if self._w is not None:
            self._set_weight(u, v, w)
        return True

    def _set_weight(self, u, v, w):
        self._w[u][v] = w
        if not self.directed:
            self._w[v][u] = w

    def neighbors(self, u):
        row = self._adj[u]
        i = row.find(1)
        while i != -1:
            yield i
            i = row.find(1, i + 1)

    def weighted_neighbors(self, u):
        if self._w is None:
            return super().weighted_neighbors(u)
        row = self._w[u]
        return ((v, row[v]) for v in self.neighbors(u))

    def weight(self, u, v):
        if not self._adj[u][v]:
            return None
        return self._w[u][v] if self._w is not None else 1.0

    def degree(self, u):
        return self._adj[u].count(1)


class CompactAdjacency(Representation):
    """Compressed sparse rows (CSR): the neighbors of u are targets[offsets[u]:offsets[u+1]].

    Three flat arrays instead of one Python object per vertex: 4 bytes per
    neighbor entry (+ 8 for its weight) and 8 per vertex. An undirected edge
    takes two entries, a directed one a single entry. This is what lets the
    50-million-vertex graphs fit in memory. Edges are buffered by add_edge() and
    the rows are built once, by counting sort, in finalize(); the graph is
    read-only afterwards. Rows are not sorted, so weight() scans the row: O(deg).
    """

    def __init__(self, n: int, weighted: bool = False, directed: bool = False):
        super().__init__(n, weighted, directed)
        self._src, self._dst = array("i"), array("i")
        self._wbuf = array("d") if weighted else None
        self._offsets = array("q", bytes(8 * (n + 2)))
        self._targets = array("i")
        self._weights = array("d") if weighted else None

    def add_edge(self, u, v, w=1.0):
        self._src.append(u)
        self._dst.append(v)
        if self._wbuf is not None:
            self._wbuf.append(w)
        return True

    def neighbors(self, u):
        return self._targets[self._offsets[u]:self._offsets[u + 1]]

    def weighted_neighbors(self, u):
        a, b = self._offsets[u], self._offsets[u + 1]
        if self._weights is None:
            return zip(self._targets[a:b], repeat(1.0))
        return zip(self._targets[a:b], self._weights[a:b])

    def weight(self, u, v):
        a, b = self._offsets[u], self._offsets[u + 1]
        for i in range(a, b):
            if self._targets[i] == v:
                return self._weights[i] if self._weights is not None else 1.0
        return None

    def degree(self, u):
        return self._offsets[u + 1] - self._offsets[u]

    def finalize(self):
        n, src, dst, wbuf = self.n, self._src, self._dst, self._wbuf
        count = array("q", bytes(8 * (n + 2)))  # count[u + 1] = degree(u)
        for u in src:
            count[u + 1] += 1
        if not self.directed:
            for v in dst:
                count[v + 1] += 1
        offsets = array("q", accumulate(count))
        pos = array("q", offsets)
        targets = array("i", bytes(4 * offsets[-1]))
        weights = array("d", bytes(8 * offsets[-1])) if wbuf is not None else None
        if self.directed:
            if weights is None:
                for u, v in zip(src, dst):
                    i = pos[u]; targets[i] = v; pos[u] = i + 1
            else:
                for u, v, w in zip(src, dst, wbuf):
                    i = pos[u]; targets[i] = v; weights[i] = w; pos[u] = i + 1
        elif weights is None:
            for u, v in zip(src, dst):
                i = pos[u]; targets[i] = v; pos[u] = i + 1
                i = pos[v]; targets[i] = u; pos[v] = i + 1
        else:
            for u, v, w in zip(src, dst, wbuf):
                i = pos[u]; targets[i] = v; weights[i] = w; pos[u] = i + 1
                i = pos[v]; targets[i] = u; weights[i] = w; pos[v] = i + 1
        self._src = self._dst = self._wbuf = None  # free the edge buffers
        self._offsets, self._targets, self._weights = offsets, targets, weights
        return self._drop_duplicates()

    def transposed(self):
        """Counting sort of the entries by target: O(n + m), no per-edge add_edge call.
        The rows have no repeated entries after finalize(), so neither does the result."""
        n, offsets, targets, weights = self.n, self._offsets, self._targets, self._weights
        count = array("q", bytes(8 * (n + 2)))
        for v in targets:
            count[v + 1] += 1
        new_offsets = array("q", accumulate(count))
        pos = array("q", new_offsets)
        new_targets = array("i", bytes(4 * len(targets)))
        new_weights = array("d", bytes(8 * len(targets))) if weights is not None else None
        for u in range(1, n + 1):
            for i in range(offsets[u], offsets[u + 1]):
                v = targets[i]
                j = pos[v]
                new_targets[j] = u
                if new_weights is not None:
                    new_weights[j] = weights[i]
                pos[v] = j + 1
        t = CompactAdjacency.__new__(CompactAdjacency)
        Representation.__init__(t, n, self.weighted, self.directed)
        t._src = t._dst = t._wbuf = None
        t._offsets, t._targets, t._weights = new_offsets, new_targets, new_weights
        return t

    def _drop_duplicates(self) -> int:
        offsets, targets = self._offsets, self._targets
        dup_rows = set()
        for u in range(1, self.n + 1):
            a, b = offsets[u], offsets[u + 1]
            if b - a > 1 and len(set(targets[a:b])) < b - a:
                dup_rows.add(u)
        if not dup_rows:
            return 0
        weights = self._weights
        new_offsets = array("q", bytes(8 * (self.n + 2)))
        new_targets = array("i")
        new_weights = array("d") if weights is not None else None
        for u in range(1, self.n + 1):
            a, b = offsets[u], offsets[u + 1]
            if u in dup_rows:
                best = {}
                for i in range(a, b):
                    w = weights[i] if weights is not None else 1.0
                    if w < best.get(targets[i], INF):
                        best[targets[i]] = w
                new_targets.extend(best)
                if new_weights is not None:
                    new_weights.extend(best.values())
            else:
                new_targets.extend(targets[a:b])
                if new_weights is not None:
                    new_weights.extend(weights[a:b])
            new_offsets[u + 1] = len(new_targets)
        removed = len(targets) - len(new_targets)
        self._offsets, self._targets, self._weights = new_offsets, new_targets, new_weights
        return removed if self.directed else removed // 2


REPRESENTATIONS = {"list": AdjacencyList, "matrix": AdjacencyMatrix, "csr": CompactAdjacency}


def create_representation(name: str, n: int, weighted: bool = False,
                          directed: bool = False) -> Representation:
    """Factory: maps the user's choice to the concrete class."""
    try:
        cls = REPRESENTATIONS[name]
    except KeyError:
        raise ValueError(f"invalid representation {name!r}; use {list(REPRESENTATIONS)}")
    return cls(n, weighted, directed)
