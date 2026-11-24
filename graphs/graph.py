"""Graph class: facade over a Representation (composition) and the algorithms."""
import math
from typing import Iterable, Tuple

from .representations import Representation, create_representation


class Graph:
    """Graph with vertices numbered 1..n, undirected (default) or directed.

    `edges` holds (u, v) pairs, or (u, v, w) triples when `weighted` is True.
    In a directed graph (u, v[, w]) is the single edge u -> v: neighbors(u) are
    the out-neighbors and degree(u) the out-degree. Repeated edges keep the
    lightest weight. Self-loops are dropped in undirected graphs (as in Parts 1
    and 2) but kept in directed ones, where a negative loop is a negative cycle.
    """

    def __init__(self, n: int, edges: Iterable[Tuple] = (),
                 representation: str = "list", weighted: bool = False, directed: bool = False):
        self.n = n
        self.m = 0
        self.weighted = weighted
        self.directed = directed
        self.representation = representation
        self.min_weight = math.inf  # tracked while loading: negative weights are known in O(1)
        self._rep: Representation = create_representation(representation, n, weighted, directed)
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
        if (u != v or self.directed) and self._rep.add_edge(u, v, w):
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

    def reversed(self) -> "Graph":
        """Transposed graph (every u -> v becomes v -> u), in the same representation.

        An undirected graph is its own transpose, so it is returned unchanged.
        Costs O(n + m) time and the memory of a second graph.
        """
        if not self.directed:
            return self
        rep = self._rep.transposed()
        if rep is not None:  # fast path (CSR): the arrays are rebuilt, no edge is re-added
            g = Graph.__new__(Graph)
            g.__dict__.update(self.__dict__)
            g._rep = rep
            return g
        if self.weighted:
            edges = ((v, u, w) for u in self.vertices() for v, w in self.weighted_neighbors(u))
        else:
            edges = ((v, u) for u in self.vertices() for v in self.neighbors(u))
        return Graph(self.n, edges, self.representation, self.weighted, directed=True)

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
        self._require_undirected("diameter")
        return (calculator or ApproximateDiameter()).compute(self)

    def connected_components(self):
        from .components import connected_components
        self._require_undirected("connected components")
        return connected_components(self)

    def _require_undirected(self, what: str) -> None:
        if self.directed:
            raise ValueError(f"{what} (Part 1) is defined here for undirected graphs only")

    def shortest_paths(self, source: int, queue=None):
        """Dijkstra from `source`; `queue` is a PriorityQueue class (default: IndexedMinHeap)."""
        from .shortest_paths import Dijkstra
        return (Dijkstra(queue) if queue else Dijkstra()).run(self, source)

    def shortest_path(self, u: int, v: int, queue=None):
        """(weighted distance, list of vertices) from u to v; (inf, None) if unreachable."""
        r = self.shortest_paths(u, queue)
        return r.distance_to(v), r.path_to(v)

    def shortest_paths_to(self, target: int):
        """Bellman-Ford from every vertex to `target` (negative weights allowed)."""
        from .bellman_ford import BellmanFord
        return BellmanFord().to_target(self, target)

    def all_pairs_shortest_paths(self, max_vertices=None):
        """Floyd-Warshall; refuses graphs above `max_vertices` (default: FloydWarshall's)."""
        from .floyd_warshall import FloydWarshall
        fw = FloydWarshall() if max_vertices is None else FloydWarshall(max_vertices=max_vertices)
        return fw.run(self)
