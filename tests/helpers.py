"""Small graphs and generators shared by the tests."""
import math
import os
import random
import tempfile

from graphs import Graph

REPRESENTATIONS = ("list", "matrix", "csr")

# Figure 1 of Part 2 (weights as in the PDF, including the negative edge)
FIGURE_1 = [(1, 2, 0.1), (2, 5, 0.2), (5, 3, 5), (3, 4, -9.5), (4, 5, 2.3), (1, 5, 1)]
# Figure 1 of Part 1 (unweighted)
PART1_EDGES = [(1, 2), (2, 5), (5, 3), (4, 5), (1, 5)]


def write_file(test, text: str, name: str = "graph.txt") -> str:
    """Writes text to a temporary file removed at the end of the test."""
    d = tempfile.TemporaryDirectory()
    test.addCleanup(d.cleanup)
    path = os.path.join(d.name, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def random_weighted_graph(n, m, seed, max_weight=10.0, zero_fraction=0.1, decimals=2):
    """Deterministic random graph with weights in [0, max_weight] (some zeros)."""
    rnd = random.Random(seed)
    edges = []
    for _ in range(m):
        u, v = rnd.randint(1, n), rnd.randint(1, n)
        w = 0.0 if rnd.random() < zero_fraction else round(rnd.uniform(0, max_weight), decimals)
        edges.append((u, v, w))
    return edges


def floyd_warshall(n, edges):
    """Reference all-pairs distances, O(n^3): only for tiny graphs."""
    d = [[math.inf] * (n + 1) for _ in range(n + 1)]
    for v in range(1, n + 1):
        d[v][v] = 0.0
    for u, v, w in edges:
        if u != v and w < d[u][v]:
            d[u][v] = d[v][u] = w
    for k in range(1, n + 1):
        dk = d[k]
        for i in range(1, n + 1):
            dik = d[i][k]
            if dik == math.inf:
                continue
            di = d[i]
            for j in range(1, n + 1):
                if dik + dk[j] < di[j]:
                    di[j] = dik + dk[j]
    return d


def path_weight(graph: Graph, path) -> float:
    return sum(graph.weight(a, b) for a, b in zip(path, path[1:]))


def random_directed_graph(n, m, seed, negative=True, max_weight=10.0):
    """Directed edges with negative weights but no negative cycle: w = c + p(u) - p(v)
    with c >= 0 and random potentials p, so every cycle keeps its weight sum(c) >= 0."""
    rnd = random.Random(seed)
    p = [rnd.randint(0, 20) if negative else 0 for _ in range(n + 1)]
    edges = []
    for _ in range(m):
        u, v = rnd.randint(1, n), rnd.randint(1, n)
        c = 0.0 if rnd.random() < 0.1 else float(rnd.randint(0, int(max_weight)))
        edges.append((u, v, c + p[u] - p[v]))
    return edges


def reference_directed(n, edges):
    """Textbook all-pairs reference for directed edges, independent of the library:
    for each source, n - 1 rounds over the edge list, then n more rounds that
    spread -inf from every edge still relaxable (paths through a negative cycle)."""
    d = [[math.inf] * (n + 1) for _ in range(n + 1)]
    for s in range(1, n + 1):
        row = d[s]
        row[s] = 0.0
        for _ in range(n - 1):
            for u, v, w in edges:
                if row[u] + w < row[v]:
                    row[v] = row[u] + w
        for _ in range(n):
            for u, v, w in edges:
                if row[u] != math.inf and (row[u] == -math.inf or row[u] + w < row[v]):
                    row[v] = -math.inf
    return d


def has_negative_cycle(n, edges):
    d = reference_directed(n, edges)
    return any(d[v][v] < 0 for v in range(1, n + 1))


def cycle_weight(graph: Graph, cycle) -> float:
    """Weight of a closed list [c0, c1, ..., c0], checking that every edge exists."""
    assert cycle[0] == cycle[-1], cycle
    return sum(graph.weight(a, b) for a, b in zip(cycle, cycle[1:]))
