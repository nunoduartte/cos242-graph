"""Single entry point for the Part 2 tests and case studies (no make needed).

  python3 run.py test                 unit + integration tests
  python3 run.py test-unit            Part 1 regression, weighted graphs, queues, Dijkstra
  python3 run.py test-integration     experiment scripts end to end on small generated files
  python3 run.py shortest-paths [...] case study A   (extra args go to the script)
  python3 run.py benchmark [...]      case study B
  python3 run.py collaboration [...]  case study C
  python3 run.py report               results/part2/report/
  python3 run.py memory-dijkstra [...]          extra memory of vector x heap (one process each)
  python3 run.py memory-representations [...]   list x matrix x CSR: load time and memory
  python3 run.py studies [--skip-benchmark]   A, C, B (unless skipped) and the report
  python3 run.py pipeline             resumes B (--resume), then A with validations, then the report;
                                      meant to run detached:  setsid nohup python3 run.py pipeline \
                                        > results/part2/pipeline.log 2>&1 < /dev/null &

Defaults (override with the script options, see `python3 -m experiments.<study> --help`):
data in ../T2 (or $DATA_DIR), k=100, seed 42, --budget 1200, --run-timeout 900.
"""
import subprocess
import sys

UNIT = ["tests.test_part1_regression", "tests.test_weighted_graph", "tests.test_dijkstra"]
INTEGRATION = ["tests.test_integration", "tests.test_memory", "tests.test_report"]
STUDIES = {"shortest-paths": "experiments.shortest_paths", "benchmark": "experiments.benchmark",
           "collaboration": "experiments.collaboration", "report": "experiments.report",
           "memory-dijkstra": "experiments.memory_dijkstra",
           "memory-representations": "experiments.memory_representations"}


def run(*args) -> int:
    print("$ python3", " ".join(args), flush=True)
    return subprocess.call([sys.executable, *args])


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "test":
        return run("-m", "unittest", "-v", *UNIT, *INTEGRATION)
    if cmd == "test-unit":
        return run("-m", "unittest", "-v", *UNIT)
    if cmd == "test-integration":
        return run("-m", "unittest", "-v", *INTEGRATION)
    if cmd in STUDIES:
        return run("-m", STUDIES[cmd], *rest)
    if cmd == "studies":
        order = ["shortest-paths", "collaboration"]
        if "--skip-benchmark" not in rest:
            order.append("benchmark")  # the report marks it as pending when skipped
        for study in order + ["report"]:
            code = run("-m", STUDIES[study])
            if code:
                return code
        return 0
    if cmd == "pipeline":
        for args in (["-m", STUDIES["benchmark"], "--resume", *rest],
                     ["-m", STUDIES["shortest-paths"], "--validate-timeout", "300"],
                     ["-m", STUDIES["report"]]):
            code = run(*args)
            if code:
                return code
        print("PIPELINE DONE", flush=True)
        return 0
    print(f"unknown command {cmd!r}\n{__doc__}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
