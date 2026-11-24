"""Integration: the Part 3 study scripts end to end on small generated files."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

from .helpers import random_directed_graph

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def write_graph(path, n, edges):
    with open(path, "w") as f:
        f.write(f"{n}\n")
        f.writelines(f"{u} {v} {w}\n" for u, v, w in edges)


class Part3ExperimentsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.data = os.path.join(cls._tmp.name, "data")
        cls.out = os.path.join(cls._tmp.name, "out")
        os.makedirs(cls.data)
        # grafo_W_a: negative weights, no negative cycle; grafo_W_b: a negative cycle that reaches 100
        write_graph(os.path.join(cls.data, "grafo_W_a.txt"), 120, random_directed_graph(120, 700, seed=1))
        write_graph(os.path.join(cls.data, "grafo_W_b.txt"), 120,
                    random_directed_graph(120, 700, seed=2) + [(10, 11, -50.0), (11, 10, 1.0), (11, 100, 1.0)])

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def run_module(self, module, *args):
        proc = subprocess.run([sys.executable, "-m", module, "--data-dir", self.data, *args],
                              cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc.stdout

    def read(self, *parts):
        with open(os.path.join(self.out, *parts), encoding="utf-8") as f:
            return json.load(f) if parts[-1].endswith(".json") else f.read()

    def test_1_bellman_ford_study(self):
        self.run_module("experiments.part3.bellman_ford", "--graphs", "grafo_W_a", "grafo_W_b",
                        "--out", os.path.join(self.out, "bellman_ford"))
        a = self.read("bellman_ford", "grafo_W_a.json")
        self.assertEqual([s["source"] for s in a["sources"]], [10, 20, 30])
        self.assertIsNone(a["negative_cycle_to_target"])
        self.assertEqual(a["certificate"]["status"], "ok")
        b = self.read("bellman_ford", "grafo_W_b.json")
        self.assertIsNotNone(b["negative_cycle_to_target"])
        self.assertLess(b["negative_cycle_in_graph"]["weight"], 0)
        self.assertEqual(b["sources"][0]["distance"], "-inf")  # 10 is on the cycle
        self.assertIn("−∞", self.read("bellman_ford", "table.md"))

    def test_2_floyd_warshall_study(self):
        out = os.path.join(self.out, "floyd_warshall")
        self.run_module("experiments.part3.floyd_warshall", "--graphs", "grafo_W_a", "grafo_W_b", "--out", out,
                        "--fw-workers", "3", "--timeout-for", "grafo_W_a=900")
        a = self.read("floyd_warshall", "grafo_W_a.json")
        self.assertEqual(a["fw"]["status"], "ok")
        self.assertEqual((a["timeout_s"], a["fw"]["workers"]), (900, 3))
        self.assertEqual(self.read("floyd_warshall", "grafo_W_b.json")["timeout_s"], 3600)
        self.assertEqual(sorted(a["fw"]["pairs"]), ["10", "20", "30", "40", "50"])
        b = self.read("floyd_warshall", "grafo_W_b.json")
        self.assertEqual(b["fw"]["status"], "negative cycle")
        self.assertIn("bellman_ford", b)  # same pairs by the fallback, with -inf where proven
        # a size limit below n: not run, and the record says why
        self.run_module("experiments.part3.floyd_warshall", "--graphs", "grafo_W_a", "--max-vertices", "50",
                        "--out", os.path.join(self.out, "fw_limit"))
        limited = self.read("fw_limit", "grafo_W_a.json")
        self.assertTrue(limited["fw"]["status"].startswith("não executado"))
        # the Floyd-Warshall matrix and the Bellman-Ford fallback agree
        bf = self.read("fw_limit", "grafo_W_a.json")["bellman_ford"]["pairs"]
        for i in a["vertices"]:
            for j in a["vertices"]:
                x, y = a["fw"]["pairs"][str(i)][str(j)]["distance"], bf[str(i)][str(j)]["distance"]
                if isinstance(x, str) or isinstance(y, str):
                    self.assertEqual(x, y)
                else:
                    self.assertAlmostEqual(x, y)

    def test_3_benchmark_and_resume(self):
        out = os.path.join(self.out, "benchmark")
        args = ["--graphs", "grafo_W_a", "--rounds", "2", "--out", out]
        self.run_module("experiments.part3.benchmark", *args)
        data = self.read("benchmark", "grafo_W_a.json")
        for alg in ("bellman-ford", "floyd-warshall"):
            self.assertEqual([r["status"] for r in data["runs"][alg]], ["ok", "ok"])
        log = self.run_module("experiments.part3.benchmark", *args, "--resume")
        self.assertIn("already complete", log)
        self.assertIn("Floyd-Warshall (s)", self.read("benchmark", "summary.md"))

    def test_4_all_pairs_and_report(self):
        out = os.path.join(self.out, "all_pairs")
        self.run_module("experiments.part3.all_pairs", "--graphs", "grafo_W_a", "--subgraphs", "grafo_W_a:40,80",
                        "--rounds", "2", "--out", out)
        for name in ("grafo_W_a", "grafo_W_a_1-40", "grafo_W_a_1-80"):
            data = self.read("all_pairs", f"{name}.json")
            self.assertTrue(data["digests_equal"], name)  # both algorithms gave the same matrix
        proc = subprocess.run([sys.executable, "-m", "experiments.part3.report", "--results", self.out],
                              cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = self.read("report", "results.md")
        for title in ("1. Bellman-Ford", "2. Floyd-Warshall", "4. Bellman-Ford para todos os pares"):
            self.assertIn(title, report)
        self.assertTrue(os.path.exists(os.path.join(self.out, "report", "all_pairs.svg")))


if __name__ == "__main__":
    unittest.main()
