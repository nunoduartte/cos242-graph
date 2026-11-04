"""Memory experiments: the probes, worker isolation, subgraph extraction and both scripts."""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

from experiments import memprobe
from experiments.memory_representations import induced_prefix, matrix_bytes

from .helpers import random_weighted_graph, write_file
from .test_integration import ROOT, write_graph

MB = 2**20


def allocate_and_free(size_mb, hold_s=0.0):
    block = b"x" * (size_mb * MB)  # written, so the pages are resident
    time.sleep(hold_s)
    del block


class ProbeTest(unittest.TestCase):
    def test_peak_is_seen_even_after_the_memory_is_freed(self):
        rec = {}
        with memprobe.peak_rss(rec):
            allocate_and_free(80)
        self.assertEqual(rec["peak_method"], "VmHWM after clear_refs")
        self.assertGreaterEqual(rec["peak_increase_mb"], 70)
        self.assertLess(rec["rss_after_mb"], rec["peak_rss_mb"] - 50)  # final RSS is not the peak

    def test_sampling_fallback_when_the_peak_cannot_be_reset(self):
        rec = {}
        with mock.patch.object(memprobe, "reset_peak", return_value=False):
            with memprobe.peak_rss(rec):
                allocate_and_free(80, hold_s=0.1)
        self.assertEqual(rec["peak_method"], "sampling every 5 ms")
        self.assertGreaterEqual(rec["peak_increase_mb"], 70)

    def test_values_are_recorded_when_the_block_fails(self):
        rec = {}
        with self.assertRaises(KeyError):
            with memprobe.peak_rss(rec):
                raise KeyError
        self.assertIn("peak_rss_mb", rec)

    def test_worker_failures_become_records(self):
        rec = memprobe.run_worker("experiments.no_such_module", [], timeout=60)
        self.assertTrue(rec["status"].startswith("failed"))
        rec = memprobe.run_worker("experiments.memory_dijkstra", ["--file", "/nonexistent", "--graph", "x",
                                                                  "--strategy", "heap"], timeout=60)
        self.assertTrue(rec["status"].startswith("failed"))


class SubgraphTest(unittest.TestCase):
    def test_induced_prefix(self):
        src = write_file(self, "6\n1 2 0.5\n2 5 1\n5 6 2\n3 1 0.25\n4 4 1\n2 3 7")
        dst = src + ".sub"
        self.assertEqual(induced_prefix(src, 4, dst), 4)
        with open(dst) as f:
            self.assertEqual(f.read(), "4\n1 2 0.5\n3 1 0.25\n4 4 1\n2 3 7\n")
        with self.assertRaises(ValueError):
            induced_prefix(src, 7, dst)

    def test_matrix_size(self):
        self.assertEqual(matrix_bytes(9), 900)


class MemoryScriptsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.data = os.path.join(cls._tmp.name, "data")
        os.makedirs(cls.data)
        write_graph(os.path.join(cls.data, "grafo_W_t.txt"), 3000, random_weighted_graph(3000, 20000, seed=4))

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def run_module(self, module, *args):
        proc = subprocess.run([sys.executable, "-m", module, "--data-dir", self.data, *args],
                              cwd=ROOT, capture_output=True, text=True, timeout=600)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_dijkstra_memory(self):
        out = os.path.join(self._tmp.name, "md")
        self.run_module("experiments.memory_dijkstra", "--graphs", "grafo_W_t", "--source", "7", "--out", out)
        with open(os.path.join(out, "runs.json")) as f:
            runs = json.load(f)["runs"]
        self.assertEqual([r["strategy"] for r in runs], ["vector", "heap"])
        for r in runs:
            self.assertEqual(r["status"], "ok")
            self.assertEqual((r["graph"], r["n"], r["source"]), ("grafo_W_t", 3000, 7))
            self.assertGreater(r["graph_mb"], 0)
            self.assertGreaterEqual(r["peak_rss_mb"], r["rss_before_mb"])
            self.assertGreater(r["dijkstra_s"], 0)
        self.assertEqual(runs[0]["reachable"], runs[1]["reachable"])
        with open(os.path.join(out, "runs.csv")) as f:
            self.assertEqual(len(f.read().splitlines()), 3)
        # repeating the measurement replaces it instead of duplicating it
        self.run_module("experiments.memory_dijkstra", "--graphs", "grafo_W_t", "--source", "7",
                        "--strategies", "heap", "--tracemalloc", "--out", out)
        with open(os.path.join(out, "runs.json")) as f:
            runs = json.load(f)["runs"]
        self.assertEqual(len(runs), 3)
        self.assertGreater(runs[-1]["tracemalloc_peak_mb"], 0)

    def test_dijkstra_memory_timeout_keeps_partial_peak(self):
        out = os.path.join(self._tmp.name, "md_timeout")
        self.run_module("experiments.memory_dijkstra", "--graphs", "grafo_W_t", "--strategies", "vector",
                        "--timeout", "0.001", "--out", out)
        with open(os.path.join(out, "runs.json")) as f:
            run = json.load(f)["runs"][0]
        self.assertTrue(run["status"].startswith("timeout"))
        self.assertIn("peak_rss_mb", run)
        self.assertNotIn("dijkstra_s", run)

    def test_representations(self):
        out = os.path.join(self._tmp.name, "rep")
        self.run_module("experiments.memory_representations", "--base", "grafo_W_t", "--sizes", "500", "3000",
                        "--full", "grafo_W_t", "--matrix-max-gb", "0.05", "--out", out)
        with open(os.path.join(out, "runs.json")) as f:
            data = json.load(f)
        runs = {(r["graph"], r["representation"]): r for r in data["runs"]}
        self.assertEqual(len(runs), 9)
        self.assertEqual(data["selection"]["sizes"], [500, 3000])
        for rep in ("list", "matrix", "csr"):
            self.assertEqual(runs["grafo_W_t_1-500", rep]["status"], "ok")
        self.assertTrue(runs["grafo_W_t", "matrix"]["status"].startswith("not built"))  # 9*3001^2 > 0.05 GiB
        m = {r["m"] for (g, rep), r in runs.items() if g == "grafo_W_t_1-500"}
        self.assertEqual(len(m), 1)  # every representation sees the same simple graph
        self.assertGreater(runs["grafo_W_t", "list"]["m"], runs["grafo_W_t_1-500", "list"]["m"])
        self.assertTrue(os.path.exists(os.path.join(out, "subgraphs", "grafo_W_t_1-500.txt")))


if __name__ == "__main__":
    unittest.main()
