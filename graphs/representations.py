"""Graph representations (Strategy pattern for edge storage)."""
from abc import ABC, abstractmethod
from array import array
from typing import Iterable


class Representation(ABC):
    """Common contract for the data structures that store adjacency."""

    def __init__(self, n: int):
        self.n = n

    @abstractmethod
    def add_edge(self, u: int, v: int) -> bool:
        """Insert {u, v}; return True if the edge was actually added."""

    @abstractmethod
    def neighbors(self, u: int) -> Iterable[int]:
        ...

    @abstractmethod
    def degree(self, u: int) -> int:
        ...

    def finalize(self) -> int:
        """Called after loading; returns how many duplicate edges were dropped."""
        return 0


class AdjacencyList(Representation):
    """O(n + m) memory. Repeated edges are removed in finalize() (sort + unique)."""

    def __init__(self, n: int):
        super().__init__(n)
        self._adj = [array("i") for _ in range(n + 1)]

    def add_edge(self, u, v):
        self._adj[u].append(v)
        self._adj[v].append(u)
        return True

    def neighbors(self, u):
        return self._adj[u]

    def degree(self, u):
        return len(self._adj[u])

    def finalize(self):
        removed = 0
        for u in range(1, self.n + 1):
            unique = array("i", sorted(set(self._adj[u])))
            removed += len(self._adj[u]) - len(unique)
            self._adj[u] = unique
        return removed // 2


class AdjacencyMatrix(Representation):
    """O(n^2) memory: one byte per cell. Ignores repeated edges."""

    def __init__(self, n: int):
        super().__init__(n)
        self._adj = [bytearray(n + 1) for _ in range(n + 1)]

    def add_edge(self, u, v):
        if self._adj[u][v]:
            return False
        self._adj[u][v] = self._adj[v][u] = 1
        return True

    def neighbors(self, u):
        row = self._adj[u]
        i = row.find(1)
        while i != -1:
            yield i
            i = row.find(1, i + 1)

    def degree(self, u):
        return self._adj[u].count(1)


REPRESENTATIONS = {"list": AdjacencyList, "matrix": AdjacencyMatrix}


def create_representation(name: str, n: int) -> Representation:
    """Factory: maps the user's choice to the concrete class."""
    try:
        return REPRESENTATIONS[name](n)
    except KeyError:
        raise ValueError(f"invalid representation {name!r}; use {list(REPRESENTATIONS)}")
