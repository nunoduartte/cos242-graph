"""Part 3: Floyd-Warshall, negative cycles, size limits and the equivalence with Bellman-Ford."""
import math
import unittest

from graphs import (AllPairsShortestPaths, BellmanFord, FloydWarshall, Graph, GraphTooLargeError,
                    NegativeCycleError, ShortestPaths)

from .helpers import (FIGURE_1, REPRESENTATIONS, cycle_weight, has_negative_cycle, random_directed_graph,
                      reference_directed)


class FloydWarshallTest(unittest.TestCase):
    def test_small_example(self):
        # 1 -> 2 (3), 2 -> 3 (-2), 1 -> 3 (4), 3 -> 1 (1): through k = 2, D[1][3] drops from 4 to 1
        edges = [(1, 2, 3.0), (2, 3, -2.0), (1, 3, 4.0), (3, 1, 1.0)]
        for rep in REPRESENTATIONS:
            r = FloydWarshall().run(Graph(3, edges, rep, weighted=True, directed=True))
            self.assertIsNone(r.negative_cycle)
            self.assertEqual([list(r.dist[i][1:]) for i in (1, 2, 3)],
                             [[0.0, 3.0, 1.0], [-1.0, 0.0, -2.0], [1.0, 4.0, 0.0]])
            self.assertEqual(r.path(1, 3), [1, 2, 3])
            self.assertEqual(r.path(2, 1), [2, 3, 1])
            self.assertNotEqual(r.distance(1, 2), r.distance(2, 1))  # no symmetry is assumed

    def test_random_graphs_against_reference(self):
        for seed in range(4):
            n = 30
            edges = random_directed_graph(n, 120, seed)
            self.assertFalse(has_negative_cycle(n, edges))
            ref = reference_directed(n, edges)
            for rep in REPRESENTATIONS:
                g = Graph(n, edges, rep, weighted=True, directed=True)
                r = FloydWarshall().run(g)
                with self.subTest(seed=seed, representation=rep):
                    for u in g.vertices():
                        for v in g.vertices():
                            self.assertAlmostEqual(r.distance(u, v), ref[u][v])
                            p = r.path(u, v)
                            if ref[u][v] == math.inf:
                                self.assertIsNone(p)
                            else:
                                self.assertEqual((p[0], p[-1]), (u, v))
                                self.assertAlmostEqual(
                                    sum(g.weight(a, b) for a, b in zip(p, p[1:])), ref[u][v])

    def test_rows_are_shortest_path_trees(self):
        edges = random_directed_graph(20, 70, seed=5)
        g = Graph(20, edges, weighted=True, directed=True)
        r = FloydWarshall().run(g)
        for u in g.vertices():
            t = r.tree(u)
            self.assertIsInstance(t, ShortestPaths)
            self.assertEqual(t.parent[u], 0)
            for v in g.vertices():
                p = t.parent[v]
                if v != u and p > 0:  # the tree edge is tight: D[u][p] + w(p, v) = D[u][v]
                    self.assertAlmostEqual(t.distance[p] + g.weight(p, v), t.distance[v])

    def test_disconnected_vertices(self):
        g = Graph(4, [(1, 2, 1.0), (3, 4, -1.0)], weighted=True, directed=True)
        r = FloydWarshall().run(g)
        self.assertEqual(r.distance(1, 3), math.inf)
        self.assertEqual(r.distance(2, 1), math.inf)
        self.assertIsNone(r.path(1, 4))
        self.assertEqual(r.path(3, 3), [3])

    def test_multiple_shortest_paths(self):
        edges = [(1, 2, 1.0), (2, 4, 1.0), (1, 3, -1.0), (3, 4, 3.0)]
        r = FloydWarshall().run(Graph(4, edges, weighted=True, directed=True))
        self.assertEqual(r.distance(1, 4), 2.0)
        self.assertIn(r.path(1, 4), ([1, 2, 4], [1, 3, 4]))

    def test_negative_cycle(self):
        for rep in REPRESENTATIONS:
            g = Graph(5, FIGURE_1, rep, weighted=True, directed=True)
            r = FloydWarshall().run(g)
            with self.subTest(representation=rep):
                self.assertEqual(sorted(set(r.negative_cycle)), [3, 4, 5])
                self.assertAlmostEqual(cycle_weight(g, r.negative_cycle), -2.2)
                self.assertIsNotNone(r.stopped_at)
                with self.assertRaises(NegativeCycleError):
                    r.distance(1, 2)
                with self.assertRaises(NegativeCycleError):
                    r.path(1, 2)

    def test_negative_cycle_detection_on_random_graphs(self):
        for seed in range(8):
            edges = random_directed_graph(15, 40, seed)
            if seed % 2:
                edges += [(3, 8, -25.0), (8, 12, 2.0), (12, 3, 2.0)]
            g = Graph(15, edges, "csr", weighted=True, directed=True)
            r = FloydWarshall().run(g)
            with self.subTest(seed=seed):
                self.assertEqual(r.negative_cycle is not None, has_negative_cycle(15, edges))
                if r.negative_cycle:
                    self.assertLess(cycle_weight(g, r.negative_cycle), 0)

    def test_negative_self_loop(self):
        g = Graph(3, [(1, 2, 1.0), (2, 2, -0.5)], weighted=True, directed=True)
        r = FloydWarshall().run(g)
        self.assertEqual(r.negative_cycle, [2, 2])

    def test_positive_self_loop_is_harmless(self):
        g = Graph(2, [(1, 1, 3.0), (1, 2, 1.0)], weighted=True, directed=True)
        r = FloydWarshall().run(g)
        self.assertEqual(r.distance(1, 1), 0.0)

    def test_undirected_graph(self):
        g = Graph(4, [(1, 2, 1.0), (2, 3, 2.0), (3, 4, 1.0), (1, 4, 5.0)], weighted=True)
        r = FloydWarshall().run(g)
        self.assertEqual(r.distance(4, 1), 4.0)
        self.assertEqual(r.distance(1, 4), 4.0)

    def test_size_limits(self):
        g = Graph(50, [(1, 2, 1.0)], weighted=True, directed=True)
        with self.assertRaisesRegex(GraphTooLargeError, "limit is 10 vertices"):
            FloydWarshall(max_vertices=10).run(g)
        with self.assertRaises(GraphTooLargeError):
            FloydWarshall(max_vertices=None, max_memory_bytes=1000).run(g)
        self.assertEqual(FloydWarshall.memory_bytes(2), 12 * 9)
        with self.assertRaises(GraphTooLargeError):
            g.all_pairs_shortest_paths(max_vertices=10)

    def test_graph_shortcut(self):
        g = Graph(2, [(1, 2, -1.0)], weighted=True, directed=True)
        self.assertEqual(g.all_pairs_shortest_paths().distance(1, 2), -1.0)


class ParallelFloydWarshallTest(unittest.TestCase):
    """workers > 1 must give exactly the sequential matrices (same operations per cell)."""

    def assert_same(self, a, b, n):
        for i in range(n + 1):
            self.assertEqual(list(a.dist[i]), list(b.dist[i]))
            self.assertEqual(list(a.pred[i]), list(b.pred[i]))

    def test_identical_to_sequential(self):
        for seed, (n, m) in enumerate([(40, 200), (57, 400), (90, 300)]):
            g = Graph(n, random_directed_graph(n, m, seed), "csr", weighted=True, directed=True)
            seq = FloydWarshall().run(g)
            for workers in (2, 3, 8):
                stages = []
                fw = FloydWarshall(workers=workers, on_stage=lambda k, rows: stages.append((k, rows)))
                par = fw.run(g)
                with self.subTest(seed=seed, workers=workers):
                    self.assertIsInstance(par.dist[1], memoryview)
                    self.assert_same(seq, par, n)
                    self.assertEqual([k for k, _ in stages], list(range(1, n + 1)))
                    self.assertEqual(fw.rows_done, sum(r for _, r in stages))
                    self.assertEqual(par.path(1, n), seq.path(1, n))
                    self.assertEqual(par.tree(2).distance, seq.tree(2).distance)

    def test_rows_done_matches_sequential(self):
        g = Graph(50, random_directed_graph(50, 150, seed=4), "list", weighted=True, directed=True)
        seq, par = FloydWarshall(), FloydWarshall(workers=4)
        seq.run(g)
        par.run(g)
        self.assertEqual(seq.rows_done, par.rows_done)

    def test_same_negative_cycle_as_sequential(self):
        for seed in range(6):
            edges = random_directed_graph(30, 90, seed) + [(3, 8, -25.0), (8, 12, 2.0), (12, 3, 2.0),
                                                           (20, 21, -9.0), (21, 20, 1.0)]
            g = Graph(30, edges, "csr", weighted=True, directed=True)
            seq = FloydWarshall().run(g)
            par = FloydWarshall(workers=5).run(g)
            with self.subTest(seed=seed):
                self.assertEqual(par.negative_cycle, seq.negative_cycle)
                self.assertEqual(par.stopped_at, seq.stopped_at)
        g = Graph(5, FIGURE_1, weighted=True, directed=True)
        self.assertEqual(FloydWarshall(workers=3).run(g).negative_cycle, FloydWarshall().run(g).negative_cycle)

    def test_more_workers_than_vertices(self):
        g = Graph(3, [(1, 2, 1.0), (2, 3, -2.0)], weighted=True, directed=True)
        self.assertEqual(FloydWarshall(workers=16).run(g).distance(1, 3), -1.0)


def _available(module):
    try:
        __import__(module)
        return True
    except ImportError:
        return False


class AcceleratedEnginesTest(unittest.TestCase):
    """engine="numpy" / "numba" (optional): exactly the sequential matrices, paths and cycles.
    Skipped when the optional dependency is not installed."""

    ENGINES = [e for e, mod in (("numpy", "numpy"), ("numba", "numba")) if _available(mod)]

    def setUp(self):
        if not self.ENGINES:
            self.skipTest("NumPy/Numba not installed (optional engines)")

    def runs(self, g):
        for engine in self.ENGINES:
            for workers in (1, 4):
                yield engine, workers, FloydWarshall(engine=engine, workers=workers).run(g)

    def test_identical_matrices_and_paths(self):
        for seed, (n, m) in enumerate([(40, 200), (57, 400), (300, 1500), (90, 300)]):
            edges = random_directed_graph(n, m, seed)
            g = Graph(n, edges, "csr", weighted=True, directed=True)
            seq = FloydWarshall(max_vertices=None).run(g)
            for engine, workers, r in self.runs(g):
                with self.subTest(seed=seed, engine=engine, workers=workers):
                    for i in range(n + 1):
                        self.assertEqual(r.dist[i].tolist(), list(seq.dist[i]))
                        self.assertEqual(r.pred[i].tolist(), list(seq.pred[i]))
                    for u in (1, 2, n):
                        self.assertEqual(r.tree(u).distance, seq.tree(u).distance)
                        for v in (1, n // 2, n):
                            self.assertEqual(r.path(u, v), seq.path(u, v))
                            self.assertIsInstance(r.distance(u, v), float)

    def test_rows_done_and_stages(self):
        g = Graph(60, random_directed_graph(60, 200, seed=3), "list", weighted=True, directed=True)
        seq = FloydWarshall()
        seq.run(g)
        for engine in self.ENGINES:
            stages = []
            fw = FloydWarshall(engine=engine, workers=3, on_stage=lambda k, r: stages.append(k))
            fw.run(g)
            self.assertEqual(fw.rows_done, seq.rows_done, engine)
            self.assertEqual(stages, list(range(1, 61)))

    def test_same_negative_cycle(self):
        for seed in range(6):
            edges = random_directed_graph(30, 90, seed) + [(3, 8, -25.0), (8, 12, 2.0), (12, 3, 2.0),
                                                           (20, 21, -9.0), (21, 20, 1.0)]
            g = Graph(30, edges, "csr", weighted=True, directed=True)
            seq = FloydWarshall().run(g)
            for engine, workers, r in self.runs(g):
                with self.subTest(seed=seed, engine=engine, workers=workers):
                    self.assertEqual(r.negative_cycle, seq.negative_cycle)
                    self.assertTrue(all(type(v) is int for v in r.negative_cycle))
                    self.assertEqual(r.stopped_at, seq.stopped_at)
        g = Graph(3, [(1, 2, 1.0), (2, 2, -0.5)], weighted=True, directed=True)
        for engine, workers, r in self.runs(g):
            self.assertEqual(r.negative_cycle, FloydWarshall().run(g).negative_cycle)

    def test_unknown_engine(self):
        with self.assertRaises(ValueError):
            FloydWarshall(engine="fortran")


class BellmanFordVsFloydWarshallTest(unittest.TestCase):
    def test_all_pairs_bellman_ford_equals_floyd_warshall(self):
        for seed in range(3):
            edges = random_directed_graph(30, 140, seed)
            for rep in REPRESENTATIONS:
                g = Graph(30, edges, rep, weighted=True, directed=True)
                fw = FloydWarshall().run(g)
                bf = BellmanFord().all_pairs(g)
                with self.subTest(seed=seed, representation=rep):
                    self.assertIsInstance(bf, AllPairsShortestPaths)
                    for u in g.vertices():
                        for v in g.vertices():
                            self.assertAlmostEqual(bf.distance(u, v), fw.distance(u, v))

    def test_bellman_ford_to_target_is_a_floyd_warshall_column(self):
        edges = random_directed_graph(25, 90, seed=6)
        g = Graph(25, edges, "csr", weighted=True, directed=True)
        fw = FloydWarshall().run(g)
        rev = g.reversed()
        for t in g.vertices():
            r = BellmanFord().to_target(g, t, rev)
            for v in g.vertices():
                self.assertAlmostEqual(r.distance_from(v), fw.distance(v, t))

    def test_both_stop_on_a_negative_cycle(self):
        g = Graph(5, FIGURE_1, weighted=True, directed=True)
        bf = BellmanFord().all_pairs(g)
        self.assertLess(cycle_weight(g, bf.negative_cycle), 0)
        self.assertEqual(bf.stopped_at, 1)  # found in the very first source
        with self.assertRaises(NegativeCycleError):
            bf.distance(1, 2)

    def test_all_pairs_size_limit(self):
        g = Graph(20, [(1, 2, 1.0)], weighted=True, directed=True)
        with self.assertRaises(GraphTooLargeError):
            BellmanFord().all_pairs(g, max_vertices=10)


if __name__ == "__main__":
    unittest.main()
