"""Regression tests for the Part 1 features (unweighted graphs)."""
import unittest

from graphs import (BFS, DFS, ApproximateDiameter, DegreeStats, ExactDiameter, Graph, GraphReader,
                    ReportWriter)

from .helpers import PART1_EDGES, REPRESENTATIONS, write_file


class Part1Test(unittest.TestCase):
    def graphs(self, n=5, edges=PART1_EDGES):
        for rep in REPRESENTATIONS:
            with self.subTest(representation=rep):
                yield Graph(n, edges, rep)

    def test_read_unweighted_file_figure_1(self):
        path = write_file(self, "5\n1 2\n2 5\n5 3\n4 5\n1 5\n")
        for rep in REPRESENTATIONS:
            g = GraphReader.read(path, rep)
            self.assertFalse(g.weighted)
            self.assertEqual((g.n, g.m), (5, 5))
            self.assertEqual(sorted(g.neighbors(5)), [1, 2, 3, 4])

    def test_degree_stats(self):
        for g in self.graphs():
            s = DegreeStats.of(g)
            self.assertEqual((s.vertices, s.edges, s.min_degree, s.max_degree), (5, 5, 1, 4))
            self.assertEqual((s.mean_degree, s.median_degree), (2.0, 2))

    def test_duplicates_and_self_loops_are_dropped(self):
        for g in self.graphs(4, [(1, 2), (2, 1), (1, 2), (3, 3), (3, 4)]):
            self.assertEqual(g.m, 2)
            self.assertEqual(list(g.neighbors(1)), [2])
            self.assertEqual(g.degree(3), 1)

    def test_bfs_tree_and_levels(self):
        for g in self.graphs():
            r = g.search(1, BFS())
            self.assertEqual(r.level[1:], [0, 1, 2, 2, 1])
            self.assertEqual(r.parent[1:], [0, 1, 5, 5, 1])

    def test_dfs_tree(self):
        for g in self.graphs():
            r = g.search(1, DFS())
            self.assertEqual(r.parent[1:], [0, 1, 5, 5, 2])
            self.assertEqual(r.level[1:], [0, 1, 3, 3, 2])

    def test_distance_and_unreachable(self):
        for g in self.graphs(6):  # vertex 6 is isolated
            self.assertEqual(g.distance(1, 3), 2)
            self.assertEqual(g.distance(1, 6), -1)

    def test_components_sorted_by_size(self):
        for g in self.graphs(8, PART1_EDGES + [(6, 7)]):
            comps = g.connected_components()
            self.assertEqual([len(c) for c in comps], [5, 2, 1])
            self.assertEqual(sorted(comps[1]), [6, 7])

    def test_diameters(self):
        path = [(i, i + 1) for i in range(1, 10)]  # path with 10 vertices
        for g in self.graphs(10, path):
            self.assertEqual(g.diameter(ExactDiameter()), 9)
            self.assertEqual(g.diameter(ApproximateDiameter()), 9)

    def test_report_files(self):
        path = write_file(self, "")
        g = Graph(5, PART1_EDGES)
        ReportWriter.summary(g, path)
        with open(path) as f:
            text = f.read()
        self.assertIn("Number of edges: 5", text)
        self.assertIn("Component 1 (size 5): 1 2 3 4 5", text)
        ReportWriter.tree(g.search(1), "BFS", path)
        with open(path) as f:
            self.assertEqual(f.read().splitlines()[1:3], ["1 - 0", "2 1 1"])

    def test_invalid_representation(self):
        with self.assertRaises(ValueError):
            Graph(3, [], "tree")


if __name__ == "__main__":
    unittest.main()
