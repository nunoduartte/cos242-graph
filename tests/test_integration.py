"""Integration: the experiment scripts end to end on small generated files."""
import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest

from experiments.common import RunTimeout, time_limit

from .helpers import random_weighted_graph

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def write_graph(path, n, edges):
    with open(path, "w") as f:
        f.write(f"{n}\n")
        f.writelines(f"{u} {v} {w}\n" for u, v, w in edges)


class ExperimentsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.data = os.path.join(cls._tmp.name, "data")
        cls.out = os.path.join(cls._tmp.name, "out")
        os.makedirs(cls.data)
        # vertex 70 is isolated: 10 cannot reach it
        write_graph(os.path.join(cls.data, "grafo_W_a.txt"), 70,
                    [(u, v, w) for u, v, w in random_weighted_graph(69, 400, seed=1)])
        write_graph(os.path.join(cls.data, "grafo_W_b.txt"), 80, random_weighted_graph(60, 300, seed=2))
        write_graph(os.path.join(cls.data, "rede.txt"), 5, [(1, 2, 0.5), (2, 3, 1.0), (1, 3, 2.0), (4, 5, 1.0)])
        with open(os.path.join(cls.data, "nomes.txt"), "w", encoding="utf-8") as f:
            f.write("1,Ana A. Silva\n2,Bruno B.\n3,Éva Tardos\n4,Alan M. Turing\n5,M. Newman\n")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def run_module(self, module, *args):
        proc = subprocess.run([sys.executable, "-m", module, "--data-dir", self.data, *args],
                              cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc.stdout

    def test_shortest_paths_study(self):
        out = os.path.join(self.out, "sp")
        self.run_module("experiments.shortest_paths", "--graphs", "grafo_W_a", "grafo_W_b",
                        "--targets", "20", "70", "--out", out)
        with open(os.path.join(out, "table.csv")) as f:
            rows = list(csv.DictReader(f))
        self.assertEqual([(r["graph"], r["target"]) for r in rows],
                         [("grafo_W_a", "20"), ("grafo_W_a", "70"), ("grafo_W_b", "20"), ("grafo_W_b", "70")])
        self.assertEqual(rows[1]["path"], "no path")
        self.assertTrue(rows[0]["path"].startswith("10 ") and rows[0]["path"].endswith(" 20"))
        for g in ("grafo_W_a", "grafo_W_b"):
            with open(os.path.join(out, f"{g}.json")) as f:
                self.assertEqual(json.load(f)["validation"]["status"], "equal")
        with open(os.path.join(out, "table.md"), encoding="utf-8") as f:
            self.assertIn("inalcançável", f.read())

    def test_benchmark(self):
        out = os.path.join(self.out, "bench")
        self.run_module("experiments.benchmark", "--graphs", "grafo_W_b", "--k", "5", "--seed", "3",
                        "--out", out)
        with open(os.path.join(out, "runs.csv")) as f:
            runs = list(csv.DictReader(f))
        self.assertEqual(len(runs), 10)
        self.assertTrue(all(r["status"] == "ok" for r in runs))
        vector = [r["source"] for r in runs if r["strategy"] == "vector"]
        heap = [r["source"] for r in runs if r["strategy"] == "heap"]
        self.assertEqual(vector, heap)  # same sources, same order
        with open(os.path.join(out, "summary.csv")) as f:
            summary = next(csv.DictReader(f))
        self.assertEqual((summary["k"], summary["seed"], summary["paired_runs"]), ("5", "3", "5"))
        self.assertGreater(float(summary["speedup"]), 0)

    def test_benchmark_resume_keeps_saved_runs(self):
        out = os.path.join(self.out, "bench_resume")
        args = ["--graphs", "grafo_W_b", "--k", "4", "--out", out]
        self.run_module("experiments.benchmark", *args)
        path = os.path.join(out, "grafo_W_b.json")
        with open(path) as f:
            data = json.load(f)
        data["runs"] = data["runs"][:2]  # as if killed after two vector runs
        with open(path, "w") as f:
            json.dump(data, f)
        self.run_module("experiments.benchmark", *args, "--resume")
        with open(path) as f:
            resumed = json.load(f)["runs"]
        self.assertEqual(resumed[:2], data["runs"])
        self.assertEqual([(r["strategy"], r["run"]) for r in resumed],
                         [("vector", i) for i in range(4)] + [("heap", i) for i in range(4)])
        self.assertTrue(all(r["status"] == "ok" for r in resumed))
        log = self.run_module("experiments.benchmark", *args, "--resume")
        self.assertIn("already complete", log)
        proc = subprocess.run([sys.executable, "-m", "experiments.benchmark", "--data-dir", self.data,
                               *args, "--seed", "7", "--resume"], cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)  # other settings: refuses to mix the results

    def test_benchmark_records_timeouts_instead_of_estimating(self):
        out = os.path.join(self.out, "bench_timeout")
        self.run_module("experiments.benchmark", "--graphs", "grafo_W_b", "--k", "3",
                        "--strategies", "vector", "--run-timeout", "1e-6", "--out", out)
        with open(os.path.join(out, "runs.csv")) as f:
            runs = list(csv.DictReader(f))
        self.assertTrue(runs[0]["status"].startswith("timeout"))
        self.assertEqual(runs[0]["seconds"], "")
        self.assertTrue(all(r["status"].startswith("not run") for r in runs[1:]))
        with open(os.path.join(out, "summary.md"), encoding="utf-8") as f:
            self.assertIn("timeout", f.read())

    def test_collaboration_study(self):
        out = os.path.join(self.out, "collab")
        self.run_module("experiments.collaboration", "--graph", "rede", "--names", "nomes.txt",
                        "--source", "Ana A. Silva", "--targets", "Éva Tardos", "Alan M. Turing", "Ninguém",
                        "--out", out)
        with open(os.path.join(out, "result.json"), encoding="utf-8") as f:
            rows = json.load(f)["rows"]
        self.assertEqual([r["status"] for r in rows], ["ok", "unreachable", "not found"])
        self.assertEqual(rows[0]["distance"], 1.5)
        self.assertEqual(rows[0]["path_names"], ["Ana A. Silva", "Bruno B.", "Éva Tardos"])


class CertificateTest(unittest.TestCase):
    def test_accepts_dijkstra_and_rejects_tampered_trees(self):
        from experiments.shortest_paths import certificate
        from graphs import Graph
        g = Graph(40, random_weighted_graph(35, 120, seed=5), "csr", weighted=True)
        r = g.shortest_paths(1)
        self.assertEqual(certificate(g, r)["status"], "ok")
        v = next(v for v in range(2, 36) if r.reachable(v))
        r.distance[v] += 0.5  # too long: some edge or parent check must notice
        self.assertEqual(certificate(g, r)["status"], "FAILED")
        r = g.shortest_paths(1)
        r.distance[v], r.parent[v] = float("inf"), -1  # reachable vertex marked unreachable
        self.assertEqual(certificate(g, r)["status"], "FAILED")


class TimeLimitTest(unittest.TestCase):
    def test_interrupts_a_long_loop(self):
        with self.assertRaises(RunTimeout):
            with time_limit(0.05):
                while True:
                    pass

    def test_no_limit(self):
        with time_limit(None):
            x = sum(range(1000))
        self.assertEqual(x, 499500)


if __name__ == "__main__":
    unittest.main()
