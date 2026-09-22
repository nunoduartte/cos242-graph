"""Graph class: facade over a Representation (composition) and the algorithms."""
from typing import Iterable, Tuple

from .representations import Representation, create_representation


class Graph:
    """Simple undirected graph with vertices numbered 1..n."""

    def __init__(self, n: int, edges: Iterable[Tuple[int, int]] = (),
                 representation: str = "list"):
        self.n = n
        self.m = 0
        self._rep: Representation = create_representation(representation, n)
        for u, v in edges:
            self.add_edge(u, v)
        self.m -= self._rep.finalize()  # drop duplicate edges present in the input

    def add_edge(self, u: int, v: int) -> None:
        if u != v and self._rep.add_edge(u, v):  # ignore self-loops
            self.m += 1

    def neighbors(self, u: int):
        return self._rep.neighbors(u)

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
