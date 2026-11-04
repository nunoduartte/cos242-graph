from dataclasses import dataclass
from typing import List, Optional, Type

from .priority_queues import INF, IndexedMinHeap, PriorityQueue


class NegativeWeightError(NotImplementedError):
    """Raised for graphs with negative weights, which Dijkstra does not handle."""


@dataclass
class ShortestPaths:
    source: int
    distance: List[float]
    parent: List[int]

    def reachable(self, v: int) -> bool:
        return self.parent[v] >= 0

    def distance_to(self, v: int) -> float:
        return self.distance[v]

    def path_to(self, v: int) -> Optional[List[int]]:
        """Vertices from the source to v, both included; None if unreachable."""
        if not self.reachable(v):
            return None
        path = [v]
        while v != self.source:
            v = self.parent[v]
            path.append(v)
        path.reverse()
        return path


class Dijkstra:

    def __init__(self, queue: Type[PriorityQueue] = IndexedMinHeap):
        self.queue = queue
        self.name = f"Dijkstra ({queue.name})"

    def run(self, graph, source: int) -> ShortestPaths:
        if not 0 < source <= graph.n:
            raise ValueError(f"source {source} is outside 1..{graph.n}")
        if graph.has_negative_weights():
            raise NegativeWeightError(
                f"the graph has negative weights (minimum {graph.min_weight}); "
                "shortest paths with negative weights are not implemented yet")
        dist = [INF] * (graph.n + 1)
        parent = [-1] * (graph.n + 1)
        dist[source], parent[source] = 0.0, 0
        q = self.queue(graph.n)
        q.insert(source, 0.0)
        insert, decrease_key, pop_min = q.insert, q.decrease_key, q.pop_min
        neighbors = graph.weighted_neighbors
        while len(q):
            u = pop_min()
            du = dist[u]
            for v, w in neighbors(u):
                d = du + w
                if d < dist[v]:  # never true for a finished vertex, since w >= 0
                    if dist[v] == INF:
                        insert(v, d)
                    else:
                        decrease_key(v, d)
                    dist[v], parent[v] = d, u
        return ShortestPaths(source, dist, parent)
