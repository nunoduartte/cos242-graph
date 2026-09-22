"""Diameter computation (Strategy): exact or approximate, both BFS-based."""
import random
from abc import ABC, abstractmethod

from .search import BFS


class DiameterCalculator(ABC):
    def __init__(self):
        self._bfs = BFS()

    @abstractmethod
    def compute(self, graph) -> int:
        ...


class ExactDiameter(DiameterCalculator):
    """BFS from every vertex: O(n(n+m)). Only for small graphs."""

    def compute(self, graph):
        return max(self._bfs.run(graph, s).eccentricity() for s in graph.vertices())


class ApproximateDiameter(DiameterCalculator):
    """Lower bound via repeated double sweep, run inside every connected component.

    The diameter of a disconnected graph is the largest finite distance, so it is
    the maximum over the components. Each component gets `attempts` sweeps from
    random start vertices; a component is only visited by BFS, so the total cost
    stays O(attempts * (n + m)).
    """

    def __init__(self, attempts: int = 5, seed: int = 0):
        super().__init__()
        self.attempts = attempts
        self._rnd = random.Random(seed)

    def compute(self, graph):
        return max(self._sweep(graph, comp) for comp in graph.connected_components())

    def _sweep(self, graph, component) -> int:
        best = 0
        for _ in range(min(self.attempts, len(component))):
            current = self._bfs.run(graph, self._rnd.choice(component))
            while True:  # repeat from the farthest vertex while it grows
                nxt = self._bfs.run(graph, current.farthest())
                if nxt.eccentricity() <= current.eccentricity():
                    break
                current = nxt
            best = max(best, current.eccentricity())
        return best
