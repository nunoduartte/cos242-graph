"""Report consolidation: Tables A-D and charts from result files (synthetic, nothing measured)."""
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from experiments.common import environment, write_json
from experiments.tables import br, csr_bytes, matrix_bytes

from .test_integration import ROOT


def run(strategy, i, source, seconds=None, status="ok"):
    r = {"strategy": strategy, "run": i, "source": source, "seconds": seconds, "status": status}
    if status.startswith("timeout"):
        r["interrupted_after_s"] = 900.0
    return r


class ReportTest(unittest.TestCase):
    def test_tables_and_charts(self):
        with tempfile.TemporaryDirectory() as res:
            for d in ("benchmarks", "memory_dijkstra", "representations"):
                os.makedirs(os.path.join(res, d))
            write_json(os.path.join(res, "benchmarks", "grafo_W_x.json"), {
                "graph": "grafo_W_x", "n": 1000, "m": 5000, "k": 3, "seed": 42, "sources": [5, 6, 7],
                "representation": "csr", "load_s": 1.5, "memory_mb": 0.2, "environment": environment(),
                "runs": [run("vector", 0, 5, status="timeout (> 900 s)"),
                         run("vector", 1, 6, status="not run (previous run timed out)"),
                         run("vector", 2, 7, status="not run (previous run timed out)"),
                         run("heap", 0, 6, 20.0), run("heap", 1, 5, 30.0),
                         run("heap", 2, 7, status="not run (budget)")]})
            write_json(os.path.join(res, "memory_dijkstra", "runs.json"), {"runs": [
                {"graph": "grafo_W_3", "strategy": "heap", "source": 10, "status": "ok", "rss_before_mb": 160,
                 "peak_rss_mb": 170, "peak_increase_mb": 10, "dijkstra_s": 1.6}]})
            write_json(os.path.join(res, "representations", "runs.json"), {"runs": [
                {"graph": "g_1-100", "n": 100, "m": 300, "representation": rep, "status": "ok", "load_s": 0.1,
                 "graph_mb": mb, "peak_increase_mb": peak} for rep, mb, peak in
                (("list", 1.0, 1.0), ("matrix", 5.0, 5.0), ("csr", 0.8, 2.0))] + [
                {"graph": "g", "n": 10**5, "representation": "matrix", "status": "not built: too big"},
                {"graph": "g", "n": 10**5, "m": 10**6, "representation": "list", "status": "ok", "load_s": 2,
                 "graph_mb": 30, "peak_increase_mb": 30},
                {"graph": "g", "n": 10**5, "m": 10**6, "representation": "csr", "status": "ok", "load_s": 2,
                 "graph_mb": 20, "peak_increase_mb": 50}]})
            proc = subprocess.run([sys.executable, "-m", "experiments.report", "--results", res], cwd=ROOT,
                                  capture_output=True, text=True, timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            with open(os.path.join(res, "report", "results.md"), encoding="utf-8") as f:
                md = f.read()
            for title in ("Tabela A", "Tabela B", "Tabela C", "Tabela D"):
                self.assertIn(title, md)
            self.assertIn("> 30,0× (limite inferior)", md)  # 900 s / heap time on the same source (5)
            self.assertIn("| 0 / 2 |", md)
            self.assertIn("| grafo_W_7 | vetor e heap | - | - | - | - | não medido |", md)
            self.assertIn("83,8 GiB", md)  # matrix of n = 10^5, formula only
            self.assertIn("PENDENTE: estudo ainda não executado", md)  # study A was not given
            for svg in ("benchmark.svg", "representations.svg", "construction_peak.svg"):
                ET.parse(os.path.join(res, "report", svg))  # well-formed

    def test_formulas_and_format(self):
        self.assertEqual(csr_bytes(10, 7), 8 * 12 + 24 * 7)
        self.assertEqual(matrix_bytes(9), 900)
        self.assertEqual(br(1234567.891, 1), "1.234.567,9")
        self.assertEqual(br(None), "-")


if __name__ == "__main__":
    unittest.main()
