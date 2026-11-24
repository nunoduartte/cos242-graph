"""Bellman-Ford: shortest paths with negative weights and negative-cycle detection.

The assignment asks for the distance and shortest path from every vertex to
one target t. Distances to t in G are distances from t in the transposed graph
G^T, so the core below is the usual single-source algorithm, run on G^T from t;
there the parent of v is the next vertex after v on a shortest path v -> t in G.
Undirected graphs are their own transpose (Graph.reversed() returns them).

The core works in passes. Pass p relaxes the out-edges of the vertices whose
distance changed in pass p - 1, updating `dist` in place. After pass p every
distance is at most the weight of the lightest path with <= p edges, so without
a negative cycle nothing changes after pass n - 1 and a change in pass n proves
a negative cycle. Optimizations (each can be switched off to measure it):

  early_stop       stop as soon as a pass changes nothing (no n - 1 passes
                   when the paths have few edges).
  active_vertices  scan only the vertices changed in the previous pass instead
                   of all m edges: an edge (u, v) can only lower dist[v] if
                   dist[u] changed since it was last relaxed.
  check_cycles     look for a cycle in the parent pointers after passes 1, 2, 4,
                   8, ...; a cycle there always has negative weight, so a
                   negative cycle is found long before pass n. O(n) per check
                   and O(log passes) checks.
"""
from collections import deque
from dataclasses import dataclass
from typing import List, Optional

from .shortest_paths import ShortestPaths

INF = float("inf")


@dataclass
class ShortestPathsTo:
    """Result of Bellman-Ford to `target`.

    distance[v]   weight of a shortest path v -> target; inf if v cannot reach
                  the target; -inf if v reaches the negative cycle found.
    successor[v]  next vertex after v on that path (the tree of shortest paths,
                  rooted at the target); 0 for the target, -1 if none.
    negative_cycle  None, or a negative cycle that can reach the target, as a
                  closed list of vertices in edge order [c0, c1, ..., c0].

    When a negative cycle is found the run stops: the vertices that reach it get
    -inf, and the other finite values are only upper bounds (`exact` is False).
    """
    target: int
    distance: List[float]
    successor: List[int]
    negative_cycle: Optional[List[int]] = None
    passes: int = 0
    relaxations: int = 0

    @property
    def exact(self) -> bool:
        return self.negative_cycle is None

    def distance_from(self, v: int) -> float:
        return self.distance[v]

    def path_from(self, v: int) -> Optional[List[int]]:
        """Vertices from v to the target, both included; None if there is no
        shortest path (target unreachable, or a negative cycle on the way)."""
        d = self.distance[v]
        if d == INF or d == -INF or self.successor[v] < 0:
            return None
        path = [v]
        while v != self.target:
            v = self.successor[v]
            path.append(v)
            if len(path) > len(self.distance):  # only possible with stale values
                return None
        return path


@dataclass
class _Run:
    dist: List[float]
    parent: List[int]
    cycle: Optional[List[int]]  # in parent order: cycle[i + 1] is the parent of cycle[i]
    passes: int
    relaxations: int


class BellmanFord:
    name = "Bellman-Ford"

    def __init__(self, early_stop: bool = True, active_vertices: bool = True, check_cycles: bool = True):
        self.early_stop = early_stop
        self.active_vertices = active_vertices
        self.check_cycles = check_cycles
        self.sources_done = 0  # progress of all_pairs, for a caller that interrupts it

    def to_target(self, graph, target: int, reversed_graph=None) -> ShortestPathsTo:
        """Distances and shortest paths from every vertex to `target`.

        `reversed_graph` lets a caller that runs many targets build G^T once.
        """
        self._check_vertex(graph, target)
        rev = reversed_graph if reversed_graph is not None else graph.reversed()
        r = self._solve(rev, target)
        cycle = None
        if r.cycle is not None:
            # in G^T the parent of v is its successor in G, so parent order is edge order in G
            cycle = r.cycle + [r.cycle[0]]
            self._mark_minus_infinity(rev, r.dist, r.cycle)
        return ShortestPathsTo(target, r.dist, r.parent, cycle, r.passes, r.relaxations)

    def run(self, graph, source: int) -> ShortestPaths:
        """Classic single-source version (same core). Raises NegativeCycleError
        if a negative cycle is reachable from `source`."""
        self._check_vertex(graph, source)
        r = self._solve(graph, source)
        if r.cycle is not None:
            cycle = r.cycle[::-1]
            raise NegativeCycleError(cycle + [cycle[0]])
        return ShortestPaths(source, r.dist, r.parent)

    def all_pairs(self, graph, max_vertices: Optional[int] = 3000):
        """All-pairs distances by n runs of the same core, one per source.

        Returns the same AllPairsShortestPaths as Floyd-Warshall (distance and
        predecessor matrices), so both produce exactly the same output. Stops at
        the first negative cycle, as Floyd-Warshall does. The size limit is the
        same as Floyd-Warshall's, because the result has the same n x n matrices.
        """
        from array import array
        from .floyd_warshall import AllPairsShortestPaths, FloydWarshall
        n = graph.n
        FloydWarshall(max_vertices).check_size(n)
        dist, pred = [array("d")], [array("i")]  # row 0 unused
        self.sources_done = 0
        for s in graph.vertices():
            r = self._solve(graph, s)
            if r.cycle is not None:
                cycle = r.cycle[::-1]
                return AllPairsShortestPaths(n, dist, pred, cycle + [cycle[0]], s)
            dist.append(array("d", r.dist))
            pred.append(array("i", r.parent))
            self.sources_done = s
        return AllPairsShortestPaths(n, dist, pred)

    def find_negative_cycle(self, graph) -> Optional[List[int]]:
        """Any negative cycle of the graph, wherever it is, or None.

        Equivalent to a run from a virtual source with a 0-weight edge to every
        vertex: all distances start at 0 and every vertex starts active.
        """
        r = self._solve(graph, None)
        if r.cycle is None:
            return None
        cycle = r.cycle[::-1]
        return cycle + [cycle[0]]

    @staticmethod
    def _check_vertex(graph, v):
        if not 0 < v <= graph.n:
            raise ValueError(f"vertex {v} is outside 1..{graph.n}")

    def _solve(self, graph, root) -> _Run:
        """Single-source core on `graph` from `root` (None = virtual source)."""
        n = graph.n
        neighbors, degree = graph.weighted_neighbors, graph.degree
        if root is None:
            dist, parent = [0.0] * (n + 1), [0] * (n + 1)
            dist[0], parent[0] = INF, -1
            active = list(range(1, n + 1))
        else:
            dist, parent = [INF] * (n + 1), [-1] * (n + 1)
            dist[root], parent[root] = 0.0, 0
            active = [root]
        everything = range(1, n + 1)
        queued = [0] * (n + 1)  # pass in which v was last added to the next active list
        next_check = 1
        relaxations = passes = 0
        cycle = None
        for p in range(1, n + 1):  # pass n only proves that a negative cycle exists
            passes = p
            changed = []
            for u in (active if self.active_vertices else everything):
                du = dist[u]
                if du == INF:
                    continue
                relaxations += degree(u)
                for v, w in neighbors(u):
                    d = du + w
                    if d < dist[v]:
                        dist[v], parent[v] = d, u
                        if queued[v] != p:
                            queued[v] = p
                            changed.append(v)
            if not changed:
                if self.early_stop:
                    break
                active = changed
                continue
            if p == n:
                cycle = self._parent_cycle(parent, changed, n)
                if cycle is None:  # impossible: see _parent_cycle
                    raise RuntimeError("pass n changed a distance but the parents have no cycle")
                break
            if self.check_cycles and p == next_check:
                next_check *= 2
                cycle = self._parent_cycle(parent, changed, n)
                if cycle is not None:
                    break
            active = changed
        return _Run(dist, parent, cycle, passes, relaxations)

    @staticmethod
    def _parent_cycle(parent, starts, n) -> Optional[List[int]]:
        """A cycle in the parent pointers reachable from `starts`, or None. O(n).

        Any such cycle has negative weight: along it each dist[v] was set to
        dist[parent] + w and the parent's distance only decreased afterwards, and
        the last of those assignments was a strict decrease. Conversely, a vertex
        changed in pass n cannot have an acyclic parent chain back to the root (its
        distance would be at least the weight of a simple path, which pass n - 1
        already reached), so after pass n this always finds the cycle.
        """
        walk = [0] * (n + 1)  # id of the walk that visited v (0 = not visited)
        for wid, s in enumerate(starts, 1):
            v = s
            while v > 0 and walk[v] == 0:
                walk[v] = wid
                v = parent[v]
            if v > 0 and walk[v] == wid:  # came back to this walk: a cycle through v
                cycle, u = [v], parent[v]
                while u != v:
                    cycle.append(u)
                    u = parent[u]
                return cycle
        return None

    @staticmethod
    def _mark_minus_infinity(graph, dist, cycle) -> None:
        """Every vertex reachable from the cycle (in `graph`) gets -inf."""
        queue = deque(cycle)
        for c in cycle:
            dist[c] = -INF
        while queue:
            for v in graph.neighbors(queue.popleft()):
                if dist[v] != -INF:
                    dist[v] = -INF
                    queue.append(v)


class NegativeCycleError(ValueError):
    """Shortest paths are undefined: a negative cycle is on the way."""

    def __init__(self, cycle):
        super().__init__(f"negative cycle: {' -> '.join(map(str, cycle))}")
        self.cycle = cycle
