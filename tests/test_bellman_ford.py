"""Part 3: Bellman-Ford to a target, negative weights, negative cycles and the optimizations."""
import itertools
import math
import unittest

from graphs import BellmanFord, Dijkstra, Graph, NegativeCycleError, ShortestPaths

from .helpers import (FIGURE_1, REPRESENTATIONS, cycle_weight, has_negative_cycle, random_directed_graph,
                      reference_directed)

# every combination of (early_stop, active_vertices, check_cycles)
VARIANTS = [BellmanFord(*flags) for flags in itertools.product((True, False), repeat=3)]


def variant_name(bf):
    return f"early_stop={bf.early_stop},active={bf.active_vertices},cycles={bf.check_cycles}"


class BellmanFordToTargetTest(unittest.TestCase):
    def check_against_reference(self, n, edges, targets):
        ref = reference_directed(n, edges)
        for rep in REPRESENTATIONS:
            g = Graph(n, edges, rep, weighted=True, directed=True)
            for bf in VARIANTS:
                for t in targets:
                    with self.subTest(representation=rep, variant=variant_name(bf), target=t):
                        r = bf.to_target(g, t)
                        self.assertIsNone(r.negative_cycle)
                        for v in g.vertices():
                            self.assertAlmostEqual(r.distance_from(v), ref[v][t])
                            path = r.path_from(v)
                            if ref[v][t] == math.inf:
                                self.assertIsNone(path)
                                self.assertEqual(r.successor[v], -1)
                            else:
                                self.assertEqual((path[0], path[-1]), (v, t))
                                self.assertAlmostEqual(
                                    sum(g.weight(a, b) for a, b in zip(path, path[1:])), r.distance_from(v))

    def test_small_example_with_negative_edge(self):
        # 1 -> 2 -> 4 costs 4 - 3 = 1, cheaper than 1 -> 4 (2) and 1 -> 3 -> 4 (5)
        edges = [(1, 2, 4.0), (2, 4, -3.0), (1, 4, 2.0), (1, 3, 1.0), (3, 4, 4.0), (4, 3, 1.0)]
        for rep in REPRESENTATIONS:
            g = Graph(4, edges, rep, weighted=True, directed=True)
            r = BellmanFord().to_target(g, 4)
            self.assertEqual(r.distance[1:], [1.0, -3.0, 4.0, 0.0])
            self.assertEqual(r.successor[1:], [2, 4, 4, 0])  # next vertex toward 4
            self.assertEqual(r.path_from(1), [1, 2, 4])
            self.assertEqual(r.path_from(4), [4])
            self.assertTrue(r.exact)

    def test_random_graphs_with_negative_weights(self):
        for seed in range(3):
            edges = random_directed_graph(30, 110, seed)
            self.assertTrue(any(w < 0 for _, _, w in edges))
            self.assertFalse(has_negative_cycle(30, edges))
            self.check_against_reference(30, edges, targets=(1, 13, 30))

    def test_target_unreachable_from_some_vertices(self):
        # 3 and 4 only have edges among themselves; 5 is isolated
        edges = [(1, 2, 1.0), (2, 1, -0.5), (3, 4, 1.0), (4, 3, 1.0), (2, 3, 2.0)]
        g = Graph(5, edges, "csr", weighted=True, directed=True)
        r = BellmanFord().to_target(g, 1)
        self.assertEqual(r.distance[1:], [0.0, -0.5, math.inf, math.inf, math.inf])
        self.assertIsNone(r.path_from(3))
        self.assertIsNone(r.path_from(5))

    def test_multiple_shortest_paths(self):
        # 1 -> 2 -> 4 and 1 -> 3 -> 4 both cost 2
        edges = [(1, 2, 1.0), (2, 4, 1.0), (1, 3, -1.0), (3, 4, 3.0)]
        for bf in VARIANTS:
            r = bf.to_target(Graph(4, edges, weighted=True, directed=True), 4)
            self.assertEqual(r.distance_from(1), 2.0)
            self.assertIn(r.path_from(1), ([1, 2, 4], [1, 3, 4]))

    def test_negative_cycle_reaching_the_target(self):
        # figure 1 read as directed: 5 -> 3 -> 4 -> 5 weighs 5 - 9.5 + 2.3 = -2.2
        for rep in REPRESENTATIONS:
            g = Graph(5, FIGURE_1, rep, weighted=True, directed=True)
            for bf in VARIANTS:
                with self.subTest(representation=rep, variant=variant_name(bf)):
                    r = bf.to_target(g, 4)
                    self.assertFalse(r.exact)
                    self.assertEqual(sorted(set(r.negative_cycle)), [3, 4, 5])
                    self.assertAlmostEqual(cycle_weight(g, r.negative_cycle), -2.2)
                    # 1 reaches the cycle, so its distance to 4 is unbounded below
                    self.assertEqual(r.distance[1:], [-math.inf] * 5)
                    self.assertIsNone(r.path_from(1))

    def test_minus_infinity_only_for_vertices_that_reach_the_cycle(self):
        # cycle 2 <-> 3 (weight -1) reaches 4; vertex 5 reaches 4 without touching it; 6 is isolated
        edges = [(1, 2, 1.0), (2, 3, -2.0), (3, 2, 1.0), (3, 4, 1.0), (5, 4, 7.0)]
        g = Graph(6, edges, weighted=True, directed=True)
        ref = reference_directed(6, edges)
        r = BellmanFord().to_target(g, 4)
        self.assertIsNotNone(r.negative_cycle)
        for v in (1, 2, 3):
            self.assertEqual(r.distance_from(v), -math.inf)
            self.assertEqual(ref[v][4], -math.inf)
        self.assertEqual(r.distance[6], math.inf)

    def test_negative_cycle_that_cannot_reach_the_target(self):
        # the cycle 3 <-> 4 is downstream of the target: distances to 1 are well defined
        edges = [(2, 1, 1.0), (1, 3, 1.0), (3, 4, -5.0), (4, 3, 1.0)]
        g = Graph(4, edges, weighted=True, directed=True)
        r = BellmanFord().to_target(g, 1)
        self.assertIsNone(r.negative_cycle)
        self.assertEqual(r.distance[1:], [0.0, 1.0, math.inf, math.inf])
        cycle = BellmanFord().find_negative_cycle(g)  # the graph does have one
        self.assertEqual(sorted(set(cycle)), [3, 4])
        self.assertLess(cycle_weight(g, cycle), 0)

    def test_find_negative_cycle_on_random_graphs(self):
        for seed in range(6):
            edges = random_directed_graph(20, 60, seed)
            if seed % 2:  # plant a negative cycle on some of them
                edges += [(5, 9, -30.0), (9, 14, 1.0), (14, 5, 1.0)]
            expected = has_negative_cycle(20, edges)
            for rep in REPRESENTATIONS:
                g = Graph(20, edges, rep, weighted=True, directed=True)
                for bf in VARIANTS:
                    with self.subTest(seed=seed, representation=rep, variant=variant_name(bf)):
                        cycle = bf.find_negative_cycle(g)
                        self.assertEqual(cycle is not None, expected)
                        if cycle:
                            self.assertLess(cycle_weight(g, cycle), 0)

    def test_negative_self_loop_is_a_negative_cycle(self):
        g = Graph(2, [(1, 1, -1.0), (1, 2, 1.0)], weighted=True, directed=True)
        r = BellmanFord().to_target(g, 2)
        self.assertEqual(r.negative_cycle, [1, 1])
        self.assertEqual(r.distance_from(1), -math.inf)
        self.assertEqual(r.distance_from(2), 0.0)

    def test_undirected_negative_edge_is_a_negative_cycle(self):
        # u - v - u traverses the same edge twice: an undirected negative edge is a 2-cycle
        g = Graph(3, [(1, 2, 1.0), (2, 3, -1.0)], weighted=True)
        r = BellmanFord().to_target(g, 1)
        self.assertEqual(sorted(r.negative_cycle[:-1]), [2, 3])

    def test_undirected_graph_matches_dijkstra(self):
        edges = random_directed_graph(30, 100, seed=9, negative=False)
        g = Graph(30, edges, "csr", weighted=True)
        d = Dijkstra().run(g, 4)
        r = BellmanFord().to_target(g, 4)
        for v in g.vertices():
            self.assertAlmostEqual(r.distance_from(v), d.distance_to(v))

    def test_directed_graph_matches_dijkstra_on_the_transpose(self):
        edges = random_directed_graph(40, 160, seed=10, negative=False)
        g = Graph(40, edges, "csr", weighted=True, directed=True)
        d = Dijkstra().run(g.reversed(), 7)  # distances from 7 in G^T = distances to 7 in G
        r = BellmanFord().to_target(g, 7)
        for v in g.vertices():
            self.assertAlmostEqual(r.distance_from(v), d.distance_to(v))

    def test_reversed_graph_can_be_reused(self):
        edges = random_directed_graph(25, 80, seed=11)
        g = Graph(25, edges, weighted=True, directed=True)
        rev = g.reversed()
        for t in (1, 2, 3):
            self.assertEqual(BellmanFord().to_target(g, t, rev).distance,
                             BellmanFord().to_target(g, t).distance)

    def test_invalid_target(self):
        g = Graph(3, [(1, 2, 1.0)], weighted=True, directed=True)
        for t in (0, 4):
            with self.assertRaises(ValueError):
                BellmanFord().to_target(g, t)

    def test_graph_shortcut(self):
        g = Graph(3, [(1, 2, -1.0), (2, 3, 2.0)], weighted=True, directed=True)
        self.assertEqual(g.shortest_paths_to(3).distance[1:], [1.0, 2.0, 0.0])


class BellmanFordOptimizationsTest(unittest.TestCase):
    def test_optimizations_do_less_work(self):
        edges = random_directed_graph(60, 300, seed=12)
        g = Graph(60, edges, "csr", weighted=True, directed=True)
        plain = BellmanFord(early_stop=False, active_vertices=False, check_cycles=False).to_target(g, 1)
        early = BellmanFord(early_stop=True, active_vertices=False).to_target(g, 1)
        both = BellmanFord().to_target(g, 1)
        self.assertEqual(plain.distance, both.distance)
        self.assertEqual(early.distance, both.distance)
        self.assertEqual(plain.passes, 60)  # n - 1 passes + the pass that proves there is no cycle
        self.assertLess(early.passes, 60)
        self.assertLess(early.relaxations, plain.relaxations)
        self.assertLess(both.relaxations, early.relaxations)

    def test_parent_check_finds_the_cycle_before_pass_n(self):
        # a long path into a negative 2-cycle next to the target
        n = 200
        edges = [(v, v + 1, 1.0) for v in range(1, n - 2)] + [(n - 2, n - 1, -3.0), (n - 1, n - 2, 1.0),
                                                             (n - 1, n, 1.0)]
        g = Graph(n, edges, weighted=True, directed=True)
        with_check = BellmanFord().to_target(g, n)
        without = BellmanFord(check_cycles=False).to_target(g, n)
        self.assertEqual(sorted(set(with_check.negative_cycle)), [n - 2, n - 1])
        self.assertEqual(sorted(set(without.negative_cycle)), [n - 2, n - 1])
        self.assertLess(with_check.passes, 10)
        self.assertEqual(without.passes, n)


class BellmanFordSingleSourceTest(unittest.TestCase):
    def test_run_from_source(self):
        edges = random_directed_graph(30, 120, seed=13)
        ref = reference_directed(30, edges)
        g = Graph(30, edges, "list", weighted=True, directed=True)
        r = BellmanFord().run(g, 5)
        self.assertIsInstance(r, ShortestPaths)
        for v in g.vertices():
            self.assertAlmostEqual(r.distance_to(v), ref[5][v])

    def test_run_raises_on_negative_cycle(self):
        g = Graph(5, FIGURE_1, weighted=True, directed=True)
        with self.assertRaises(NegativeCycleError) as ctx:
            BellmanFord().run(g, 1)
        self.assertAlmostEqual(cycle_weight(g, ctx.exception.cycle), -2.2)


if __name__ == "__main__":
    unittest.main()
