"""Graph class: facade over a Representation (composition) and the algorithms."""
import math
from typing import Iterable, Tuple

from .representations import Representation, create_representation


class Graph:
    """Simple undirected graph with vertices numbered 1..n.

    `edges` holds (u, v) pairs, or (u, v, w) triples when `weighted` is True.
    """

    def __init__(self, n: int, edges: Iterable[Tuple] = (),
                 representation: str = "list", weighted: bool = False):
        self.n = n
        self.m = 0
        self.weighted = weighted
        self.min_weight = math.inf  # tracked while loading: negative weights are known in O(1)
        self._rep: Representation = create_representation(representation, n, weighted)
        add = self.add_edge
        if weighted:
            for u, v, w in edges:
                add(u, v, w)
        else:
            for u, v in edges:
                add(u, v)
        self.m -= self._rep.finalize()  # drop duplicate edges present in the input

    def add_edge(self, u: int, v: int, w: float = 1.0) -> None:
        if not (0 < u <= self.n and 0 < v <= self.n):
            raise ValueError(f"edge ({u}, {v}) has a vertex outside 1..{self.n}")
        if self.weighted:
            if not math.isfinite(w):
                raise ValueError(f"edge ({u}, {v}) has a non-finite weight {w}")
            if w < self.min_weight:
                self.min_weight = w
        if u != v and self._rep.add_edge(u, v, w):  # ignore self-loops
            self.m += 1

    def neighbors(self, u: int):
        return self._rep.neighbors(u)

    def weighted_neighbors(self, u: int):
        """(v, weight) pairs; weight 1.0 in an unweighted graph."""
        return self._rep.weighted_neighbors(u)

    def weight(self, u: int, v: int):
        """Weight of edge {u, v}, or None if it does not exist."""
        return self._rep.weight(u, v)

    def has_negative_weights(self) -> bool:
        return self.min_weight < 0

    def degree(self, u: int) -> int:
        return self._rep.degree(u)

    def vertices(self) -> range:
        return range(1, self.n + 1)

    def degrees(self):
        return [self.degree(u) for u in self.vertices()]

    # Shortcuts delegating to the algorithms (local imports avoid cycles).
    def search(self, root: int, strategy=None):
        from .search import BFS
        return (strategy or BFS()).run(self, root)

    def distance(self, u: int, v: int) -> int:
        """Distance in edges via BFS; -1 if in different components."""
        return self.search(u).level[v]

    def diameter(self, calculator=None) -> int:
        from .diameter import ApproximateDiameter
        return (calculator or ApproximateDiameter()).compute(self)

    def connected_components(self):
        from .components import connected_components
        return connected_components(self)

    def shortest_paths(self, source: int, queue=None):
        """Dijkstra from `source`; `queue` is a PriorityQueue class (default: IndexedMinHeap)."""
        from .shortest_paths import Dijkstra
        return (Dijkstra(queue) if queue else Dijkstra()).run(self, source)

    def shortest_path(self, u: int, v: int, queue=None):
        """(weighted distance, list of vertices) from u to v; (inf, None) if unreachable."""
        r = self.shortest_paths(u, queue)
        return r.distance_to(v), r.path_to(v)
