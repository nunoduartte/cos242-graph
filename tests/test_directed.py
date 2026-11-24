"""Part 3: directed weighted graphs, and BFS, DFS and Dijkstra following the edge direction."""
import math
import unittest

from graphs import BFS, DFS, Dijkstra, Graph, GraphReader, IndexedMinHeap, NegativeWeightError, VectorQueue

from .helpers import REPRESENTATIONS, random_directed_graph, reference_directed, write_file

QUEUES = (VectorQueue, IndexedMinHeap)


class DirectedGraphTest(unittest.TestCase):
    def test_file_line_is_a_single_edge_from_first_to_second(self):
        path = write_file(self, "4\n1 2 0.5\n2 3 -1.2\n3 4 2.0\n")
        for rep in REPRESENTATIONS:
            with self.subTest(representation=rep):
                g = GraphReader.read(path, rep, directed=True)
                self.assertTrue(g.directed and g.weighted)
                self.assertEqual(g.m, 3)
                self.assertEqual(g.weight(1, 2), 0.5)
                self.assertIsNone(g.weight(2, 1))  # no reverse edge is created
                self.assertEqual(g.weight(2, 3), -1.2)
                self.assertEqual(list(g.neighbors(1)), [2])
                self.assertEqual(list(g.neighbors(4)), [])
                self.assertEqual(g.degrees(), [1, 1, 1, 0])  # out-degrees

    def test_same_file_read_as_undirected_has_both_directions(self):
        path = write_file(self, "3\n1 2 0.5\n2 3 1.0\n")
        g = GraphReader.read(path, "csr")  # default: undirected, as in Parts 1 and 2
        self.assertFalse(g.directed)
        self.assertEqual(g.weight(2, 1), 0.5)
        self.assertEqual(sorted(g.neighbors(2)), [1, 3])

    def test_antiparallel_edges_are_distinct_and_parallel_keep_the_lightest(self):
        edges = [(1, 2, 3.0), (2, 1, -1.0), (1, 2, 2.0), (1, 2, 5.0)]
        for rep in REPRESENTATIONS:
            with self.subTest(representation=rep):
                g = Graph(2, edges, rep, weighted=True, directed=True)
                self.assertEqual(g.m, 2)
                self.assertEqual(g.weight(1, 2), 2.0)
                self.assertEqual(g.weight(2, 1), -1.0)

    def test_self_loops_kept_only_when_directed(self):
        for rep in REPRESENTATIONS:
            with self.subTest(representation=rep):
                d = Graph(2, [(1, 1, -2.0), (1, 2, 1.0)], rep, weighted=True, directed=True)
                self.assertEqual((d.m, d.weight(1, 1)), (2, -2.0))
                u = Graph(2, [(1, 1, -2.0), (1, 2, 1.0)], rep, weighted=True)
                self.assertEqual((u.m, u.weight(1, 1)), (1, None))

    def test_representations_agree(self):
        edges = random_directed_graph(30, 120, seed=3)
        graphs = [Graph(30, edges, rep, weighted=True, directed=True) for rep in REPRESENTATIONS]
        for u in range(1, 31):
            expected = sorted(graphs[0].weighted_neighbors(u))
            for g in graphs[1:]:
                self.assertEqual(sorted(g.weighted_neighbors(u)), expected)
        self.assertEqual(len({g.m for g in graphs}), 1)

    def test_reversed_graph(self):
        edges = random_directed_graph(25, 90, seed=4)
        for rep in REPRESENTATIONS:
            with self.subTest(representation=rep):
                g = Graph(25, edges, rep, weighted=True, directed=True)
                r = g.reversed()
                self.assertEqual((r.n, r.m, r.directed, r.representation), (g.n, g.m, True, rep))
                for u in g.vertices():
                    for v, w in g.weighted_neighbors(u):
                        self.assertEqual(r.weight(v, u), w)
                self.assertEqual(sorted((u, v) for v in r.vertices() for u in r.neighbors(v)),
                                 sorted((u, v) for u in g.vertices() for v in g.neighbors(u)))

    def test_undirected_graph_is_its_own_transpose(self):
        g = Graph(3, [(1, 2, 1.0)], weighted=True)
        self.assertIs(g.reversed(), g)

    def test_unweighted_directed_graph(self):
        g = Graph(3, [(1, 2), (2, 3)], "csr", directed=True)
        self.assertEqual(g.weight(1, 2), 1.0)
        self.assertEqual(g.reversed().weight(3, 2), 1.0)

    def test_part1_notions_are_refused_on_directed_graphs(self):
        g = Graph(3, [(1, 2), (2, 3)], directed=True)
        with self.assertRaises(ValueError):
            g.connected_components()
        with self.assertRaises(ValueError):
            g.diameter()


class DirectedSearchTest(unittest.TestCase):
    EDGES = [(1, 2), (2, 3), (3, 4), (5, 4)]  # 1 -> 2 -> 3 -> 4 <- 5

    def test_bfs_and_dfs_follow_out_edges_only(self):
        for rep in REPRESENTATIONS:
            g = Graph(5, self.EDGES, rep, directed=True)
            for S in (BFS, DFS):
                with self.subTest(representation=rep, search=S.name):
                    r = S().run(g, 1)
                    self.assertEqual(r.level[1:], [0, 1, 2, 3, -1])  # 5 only has an edge into 4
                    self.assertEqual(r.parent[1:5], [0, 1, 2, 3])
                    self.assertEqual(S().run(g, 4).level[1:], [-1, -1, -1, 0, -1])  # 4 is a sink
                    self.assertEqual(S().run(g, 5).level[1:], [-1, -1, -1, 1, 0])

    def test_direction_changes_reachability_and_distance(self):
        g = Graph(5, self.EDGES, directed=True)
        u = Graph(5, self.EDGES)
        self.assertEqual(g.distance(1, 4), 3)
        self.assertEqual(g.distance(4, 1), -1)  # unreachable against the direction
        self.assertEqual(u.distance(4, 1), 3)
        self.assertEqual(u.distance(1, 5), 4)
        self.assertEqual(g.distance(1, 5), -1)


class DirectedDijkstraTest(unittest.TestCase):
    def test_direction_changes_reachability(self):
        edges = [(1, 2, 1.0), (2, 3, 1.0), (3, 1, 5.0)]
        for rep in REPRESENTATIONS:
            g = Graph(3, edges, rep, weighted=True, directed=True)
            for Q in QUEUES:
                with self.subTest(representation=rep, queue=Q.name):
                    r = Dijkstra(Q).run(g, 1)
                    self.assertEqual(r.distance[1:], [0.0, 1.0, 2.0])
                    back = Dijkstra(Q).run(g, 3)
                    self.assertEqual(back.distance[1:], [5.0, 6.0, 0.0])  # 3 -> 1 -> 2, not 3 -> 2
                    self.assertEqual(back.path_to(2), [3, 1, 2])

    def test_unreachable_in_one_direction(self):
        g = Graph(3, [(1, 2, 1.0), (3, 2, 1.0)], "csr", weighted=True, directed=True)
        for Q in QUEUES:
            r = Dijkstra(Q).run(g, 2)
            self.assertEqual(r.distance[1:], [math.inf, 0.0, math.inf])
            self.assertIsNone(r.path_to(1))

    def test_random_directed_graphs_against_reference(self):
        for seed in range(4):
            n = 40
            edges = random_directed_graph(n, 200, seed, negative=False)
            ref = reference_directed(n, edges)
            for rep in REPRESENTATIONS:
                g = Graph(n, edges, rep, weighted=True, directed=True)
                for Q in QUEUES:
                    with self.subTest(seed=seed, representation=rep, queue=Q.name):
                        for s in (1, 7, 23):
                            r = Dijkstra(Q).run(g, s)
                            for v in g.vertices():
                                self.assertAlmostEqual(r.distance[v], ref[s][v])
                                p = r.path_to(v)
                                if p is not None:
                                    self.assertAlmostEqual(
                                        sum(g.weight(a, b) for a, b in zip(p, p[1:])), r.distance[v])

    def test_negative_weight_still_rejected(self):
        g = Graph(2, [(1, 2, -1.0)], weighted=True, directed=True)
        for Q in QUEUES:
            with self.assertRaises(NegativeWeightError):
                Dijkstra(Q).run(g, 1)


if __name__ == "__main__":
    unittest.main()
