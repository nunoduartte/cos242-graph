"""Dijkstra: priority queues, correctness and the vector x heap equivalence."""
import math
import random
import unittest

from graphs import (Dijkstra, Graph, IndexedMinHeap, NegativeWeightError, ShortestPaths, VectorQueue)

from .helpers import FIGURE_1, REPRESENTATIONS, floyd_warshall, path_weight, random_weighted_graph

QUEUES = (VectorQueue, IndexedMinHeap)


class PriorityQueueTest(unittest.TestCase):
    def test_pops_in_key_order_with_decrease_key(self):
        for Q in QUEUES:
            with self.subTest(queue=Q.name):
                q = Q(10)
                for v, k in [(3, 5.0), (7, 1.0), (1, 9.0), (4, 3.0), (9, 3.0)]:
                    q.insert(v, k)
                q.decrease_key(1, 0.5)
                q.decrease_key(3, 2.0)
                self.assertEqual(len(q), 5)
                out = [q.pop_min() for _ in range(5)]
                self.assertEqual(out[:3], [1, 7, 3])
                self.assertEqual(sorted(out[3:]), [4, 9])
                self.assertEqual(len(q), 0)

    def test_heap_sorts_random_keys(self):
        rnd = random.Random(7)
        q = IndexedMinHeap(1000)
        keys = {v: rnd.random() for v in range(1, 1001)}
        for v, k in keys.items():
            q.insert(v, k)
        for v in range(1, 1001, 3):
            keys[v] /= 2
            q.decrease_key(v, keys[v])
        popped = [q.pop_min() for _ in range(1000)]
        self.assertEqual([keys[v] for v in popped], sorted(keys.values()))
        self.assertNotIn(5, q)

    def test_heap_rejects_increase(self):
        q = IndexedMinHeap(3)
        q.insert(1, 1.0)
        with self.assertRaises(ValueError):
            q.decrease_key(1, 2.0)


class DijkstraTest(unittest.TestCase):
    def run_all(self, n, edges, source):
        """Yields (graph, result) for every representation and queue."""
        for rep in REPRESENTATIONS:
            g = Graph(n, edges, rep, weighted=True)
            for Q in QUEUES:
                with self.subTest(representation=rep, queue=Q.name):
                    yield g, Dijkstra(Q).run(g, source)

    def test_single_path(self):
        for g, r in self.run_all(4, [(1, 2, 1.5), (2, 3, 2.5), (3, 4, 1.0)], 1):
            self.assertEqual(r.distance[1:], [0.0, 1.5, 4.0, 5.0])
            self.assertEqual(r.path_to(4), [1, 2, 3, 4])

    def test_lightest_path_is_not_the_one_with_fewest_edges(self):
        edges = [(1, 4, 10.0), (1, 2, 1.0), (2, 3, 1.0), (3, 4, 1.0)]
        for g, r in self.run_all(4, edges, 1):
            self.assertEqual(r.distance_to(4), 3.0)
            self.assertEqual(r.path_to(4), [1, 2, 3, 4])
            self.assertEqual(g.distance(1, 4), 1)  # BFS still counts edges

    def test_multiple_paths_and_decrease_key(self):
        # 3 is first reached through 1-3 (6.0) and later improved through 2 (1 + 2)
        edges = [(1, 2, 1.0), (1, 3, 6.0), (2, 3, 2.0), (3, 4, 1.0), (2, 4, 5.0)]
        for g, r in self.run_all(4, edges, 1):
            self.assertEqual(r.distance[1:], [0.0, 1.0, 3.0, 4.0])
            self.assertEqual(r.parent[1:], [0, 1, 2, 3])

    def test_source_equals_destination(self):
        for g, r in self.run_all(3, [(1, 2, 1.0)], 2):
            self.assertEqual(r.distance_to(2), 0.0)
            self.assertEqual(r.path_to(2), [2])
            self.assertEqual(g.shortest_path(2, 2), (0.0, [2]))

    def test_unreachable_and_disconnected(self):
        for g, r in self.run_all(5, [(1, 2, 1.0), (3, 4, 1.0)], 1):  # 5 is isolated
            for v in (3, 4, 5):
                self.assertFalse(r.reachable(v))
                self.assertEqual(r.distance_to(v), math.inf)
                self.assertIsNone(r.path_to(v))
                self.assertEqual(r.parent[v], -1)

    def test_single_vertex(self):
        for g, r in self.run_all(1, [], 1):
            self.assertEqual(r.distance[1:], [0.0])
            self.assertEqual(r.path_to(1), [1])

    def test_decimal_weights(self):
        for g, r in self.run_all(3, [(1, 2, 0.1), (2, 3, 0.2), (1, 3, 0.35)], 1):
            self.assertAlmostEqual(r.distance_to(3), 0.3, places=12)
            self.assertEqual(r.path_to(3), [1, 2, 3])

    def test_zero_weights(self):
        edges = [(1, 2, 0.0), (2, 3, 0.0), (3, 4, 2.0), (1, 4, 3.0)]
        for g, r in self.run_all(4, edges, 1):
            self.assertEqual(r.distance[1:], [0.0, 0.0, 0.0, 2.0])
            self.assertEqual(r.path_to(4), [1, 2, 3, 4])

    def test_negative_weights_are_rejected(self):
        for rep in REPRESENTATIONS:
            g = Graph(5, FIGURE_1, rep, weighted=True)
            for Q in QUEUES:
                with self.subTest(representation=rep, queue=Q.name):
                    with self.assertRaisesRegex(NegativeWeightError, "negative weights are not implemented"):
                        Dijkstra(Q).run(g, 1)
            with self.assertRaises(NotImplementedError):  # NegativeWeightError is one
                g.shortest_paths(1)

    def test_figure_1_without_the_negative_edge(self):
        edges = [e for e in FIGURE_1 if e[2] >= 0]
        for g, r in self.run_all(5, edges, 1):
            self.assertEqual(r.path_to(3), [1, 2, 5, 3])
            self.assertAlmostEqual(r.distance_to(3), 5.3)
            self.assertAlmostEqual(r.distance_to(4), 2.6)

    def test_unweighted_graph_gives_bfs_distances(self):
        g = Graph(5, [(1, 2), (2, 5), (5, 3), (4, 5), (1, 5)])
        r = g.shortest_paths(1)
        bfs = g.search(1)
        self.assertEqual(r.distance[1:], [float(x) for x in bfs.level[1:]])

    def test_invalid_source(self):
        g = Graph(3, [(1, 2, 1.0)], weighted=True)
        for s in (0, 4):
            with self.assertRaises(ValueError):
                g.shortest_paths(s)

    def test_predecessor_tree_is_consistent(self):
        """parent[v] is on a shortest path: dist[v] = dist[parent] + w(parent, v)."""
        edges = random_weighted_graph(60, 200, seed=3)
        for g, r in self.run_all(60, edges, 1):
            for v in g.vertices():
                if r.reachable(v) and v != 1:
                    p = r.parent[v]
                    self.assertAlmostEqual(r.distance[v], r.distance[p] + g.weight(p, v), places=9)

    def test_result_object(self):
        r = ShortestPaths(2, [math.inf, 1.0, 0.0, math.inf], [-1, 2, 0, -1])
        self.assertEqual(r.path_to(1), [2, 1])
        self.assertIsNone(r.path_to(3))


class EquivalenceTest(unittest.TestCase):
    """Vector and heap must agree on distances; paths may differ on ties."""

    def check(self, n, edges, sources):
        reference = floyd_warshall(n, edges)
        for rep in REPRESENTATIONS:
            g = Graph(n, edges, rep, weighted=True)
            for s in sources:
                results = [Dijkstra(Q).run(g, s) for Q in QUEUES]
                for r in results:
                    for v in g.vertices():
                        expected = reference[s][v]
                        if expected == math.inf:
                            self.assertFalse(r.reachable(v))
                            self.assertIsNone(r.path_to(v))
                            continue
                        self.assertTrue(math.isclose(r.distance[v], expected, rel_tol=1e-9, abs_tol=1e-9))
                        path = r.path_to(v)
                        self.assertEqual((path[0], path[-1]), (s, v))
                        self.assertTrue(math.isclose(path_weight(g, path), expected,
                                                     rel_tol=1e-9, abs_tol=1e-9))
                vec, heap = results
                self.assertEqual([vec.reachable(v) for v in g.vertices()],
                                 [heap.reachable(v) for v in g.vertices()])

    def test_random_graphs_against_floyd_warshall(self):
        cases = [(1, 0), (2, 1), (8, 6), (15, 20), (30, 45), (40, 200), (25, 300)]
        for i, (n, m) in enumerate(cases):
            with self.subTest(n=n, m=m):
                self.check(n, random_weighted_graph(n, m, seed=i), [1, n // 2 + 1, n])

    def test_many_ties(self):
        # integer weights in {0, 1, 2}: many shortest paths share the same distance
        rnd = random.Random(11)
        edges = [(rnd.randint(1, 30), rnd.randint(1, 30), float(rnd.randint(0, 2))) for _ in range(90)]
        self.check(30, edges, [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
