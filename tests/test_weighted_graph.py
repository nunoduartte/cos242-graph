"""Weighted graphs: representations, reader and input validation."""
import unittest

from graphs import Graph, GraphReader, VertexLabels

from .helpers import FIGURE_1, REPRESENTATIONS, write_file


class WeightedRepresentationTest(unittest.TestCase):
    def graphs(self, n, edges):
        for rep in REPRESENTATIONS:
            with self.subTest(representation=rep):
                yield Graph(n, edges, rep, weighted=True)

    def test_figure_1_weights_are_undirected(self):
        for g in self.graphs(5, FIGURE_1):
            self.assertEqual(g.m, 6)
            for u, v, w in FIGURE_1:
                self.assertEqual(g.weight(u, v), w)
                self.assertEqual(g.weight(v, u), w)
            self.assertIsNone(g.weight(1, 3))
            self.assertEqual(sorted(g.weighted_neighbors(5)), [(1, 1.0), (2, 0.2), (3, 5.0), (4, 2.3)])

    def test_negative_weight_is_stored_and_flagged(self):
        for g in self.graphs(5, FIGURE_1):
            self.assertEqual(g.weight(4, 3), -9.5)
            self.assertTrue(g.has_negative_weights())
            self.assertEqual(g.min_weight, -9.5)

    def test_integer_decimal_and_zero_weights(self):
        for g in self.graphs(3, [(1, 2, 3), (2, 3, 0.125), (1, 3, 0)]):
            self.assertEqual(g.weight(1, 2), 3.0)
            self.assertEqual(g.weight(2, 3), 0.125)
            self.assertEqual(g.weight(3, 1), 0.0)
            self.assertFalse(g.has_negative_weights())

    def test_parallel_edges_keep_the_lightest(self):
        for g in self.graphs(3, [(1, 2, 5.0), (2, 1, 2.0), (1, 2, 7.0), (2, 3, 1.0)]):
            self.assertEqual(g.m, 2)
            self.assertEqual(g.weight(1, 2), 2.0)
            self.assertEqual(g.degree(1), 1)
            self.assertEqual(list(g.weighted_neighbors(1)), [(2, 2.0)])

    def test_self_loops_are_ignored(self):
        for g in self.graphs(2, [(1, 1, 4.0), (1, 2, 1.0)]):
            self.assertEqual(g.m, 1)
            self.assertIsNone(g.weight(1, 1))

    def test_isolated_vertices_and_components(self):
        for g in self.graphs(6, [(1, 2, 1.0), (3, 4, 2.0)]):
            self.assertEqual(g.degree(5), 0)
            self.assertEqual(list(g.weighted_neighbors(6)), [])
            self.assertEqual([len(c) for c in g.connected_components()], [2, 2, 1, 1])

    def test_part1_algorithms_still_work_on_weighted_graphs(self):
        for g in self.graphs(5, FIGURE_1):
            self.assertEqual(g.distance(1, 4), 2)  # BFS ignores weights
            self.assertEqual(g.diameter(), 2)

    def test_unweighted_graph_reports_weight_one(self):
        for rep in REPRESENTATIONS:
            g = Graph(3, [(1, 2), (2, 3)], rep)
            self.assertEqual(g.weight(1, 2), 1.0)
            self.assertEqual(sorted(g.weighted_neighbors(2)), [(1, 1.0), (3, 1.0)])

    def test_vertex_out_of_range(self):
        for edge in [(0, 1, 1.0), (1, 4, 1.0)]:
            with self.assertRaises(ValueError):
                Graph(3, [edge], weighted=True)

    def test_non_finite_weight(self):
        for w in (float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                Graph(2, [(1, 2, w)], weighted=True)


class WeightedReaderTest(unittest.TestCase):
    FIGURE_1_TEXT = "5\n1 2 0.1\n2 5 0.2\n5 3 5\n3 4 -9.5\n4 5 2.3\n1 5 1\n"

    def test_reads_figure_1_with_every_representation(self):
        path = write_file(self, self.FIGURE_1_TEXT)
        for rep in REPRESENTATIONS:
            g = GraphReader.read(path, rep)
            self.assertTrue(g.weighted)
            self.assertEqual((g.n, g.m), (5, 6))
            self.assertEqual(g.weight(3, 4), -9.5)
            self.assertEqual(g.weight(5, 3), 5.0)

    def test_weighted_detection_can_be_forced_off(self):
        path = write_file(self, self.FIGURE_1_TEXT)
        g = GraphReader.read(path, weighted=False)
        self.assertFalse(g.weighted)
        self.assertEqual(g.weight(3, 4), 1.0)

    def test_blank_lines_and_trailing_newline(self):
        path = write_file(self, "3\n\n1 2 0.5\n\n2 3 1.5\n\n")
        g = GraphReader.read(path)
        self.assertEqual((g.m, g.weight(2, 3)), (2, 1.5))

    def test_graph_without_edges(self):
        path = write_file(self, "4\n")
        g = GraphReader.read(path)
        self.assertEqual((g.n, g.m), (4, 0))

    def test_invalid_inputs(self):
        bad = {"header": "x\n1 2 1\n", "weight": "3\n1 2 abc\n", "missing weight": "3\n1 2 1\n2 3\n",
               "extra column": "3\n1 2 1 9\n", "vertex": "3\n1 9 1\n", "nan": "3\n1 2 nan\n"}
        for case, text in bad.items():
            with self.subTest(case=case), self.assertRaises(ValueError):
                GraphReader.read(write_file(self, text))

    def test_error_message_has_line_number(self):
        with self.assertRaisesRegex(ValueError, r":3: invalid edge line"):
            GraphReader.read(write_file(self, "3\n1 2 1\n2 3 x\n"))


class VertexLabelsTest(unittest.TestCase):
    def test_names_with_spaces_commas_and_accents(self):
        path = write_file(self, "1,Edsger W. Dijkstra\n2,Éva Tardos\n3,Smith, John\n")
        labels = VertexLabels.read(path)
        self.assertEqual(len(labels), 3)
        self.assertEqual(labels.id_of("Éva Tardos"), 2)
        self.assertEqual(labels.name(3), "Smith, John")
        self.assertEqual(labels.names([1, 2]), ["Edsger W. Dijkstra", "Éva Tardos"])
        self.assertIsNone(labels.id_of("Eva Tardos"))

    def test_malformed_line(self):
        with self.assertRaises(ValueError):
            VertexLabels.read(write_file(self, "1 Edsger\n"))


if __name__ == "__main__":
    unittest.main()
