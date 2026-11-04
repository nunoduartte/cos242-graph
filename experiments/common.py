"""Shared helpers for the Part 2 experiments: loading, timing limits, output files."""
import csv
import datetime
import json
import os
import platform
import signal
import sys
import time
from contextlib import contextmanager

from graphs import GraphReader

WEIGHTED_GRAPHS = ["grafo_W_3", "grafo_W_4", "grafo_W_5", "grafo_W_6", "grafo_W_7"]
DEFAULT_DATA_DIR = os.environ.get("DATA_DIR", "../T2")
DEFAULT_RESULTS = os.path.join("results", "part2")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def rss_mb() -> float:
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS"):
                return int(line.split()[1]) / 1024
    return float("nan")


def load(data_dir: str, name: str, representation: str = "csr"):
    """Reads <data_dir>/<name>.txt; returns (graph, seconds, MB added to RSS)."""
    path = os.path.join(data_dir, f"{name}.txt")
    log(f"{name}: loading {path} ({os.path.getsize(path) / 2**20:.0f} MiB) as {representation}...")
    base, t = rss_mb(), time.perf_counter()
    g = GraphReader.read(path, representation)
    seconds, memory = time.perf_counter() - t, rss_mb() - base
    log(f"{name}: n={g.n} m={g.m} in {seconds:.1f} s, +{memory:.0f} MB")
    return g, seconds, memory


class RunTimeout(Exception):
    pass


@contextmanager
def time_limit(seconds):
    """Interrupts the block with RunTimeout after `seconds` (None = no limit).

    SIGALRM is delivered between bytecodes, so a pure-Python algorithm stops
    cleanly and leaves no state behind (its partial result is discarded).
    """
    if not seconds:
        yield
        return

    def handler(signum, frame):
        raise RunTimeout()

    old = signal.signal(signal.SIGALRM, handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def environment() -> dict:
    cpu = platform.processor()
    try:
        with open("/proc/cpuinfo") as f:
            cpu = next(line.split(":", 1)[1].strip() for line in f if line.startswith("model name"))
    except (OSError, StopIteration):
        pass
    try:
        with open("/proc/meminfo") as f:
            ram_gib = int(f.readline().split()[1]) / 2**20
    except OSError:
        ram_gib = None
    return {"date": datetime.datetime.now().isoformat(timespec="seconds"),
            "python": sys.version.split()[0], "implementation": platform.python_implementation(),
            "platform": platform.platform(), "cpu": cpu,
            "ram_gib": round(ram_gib, 1) if ram_gib else None, "argv": sys.argv}


def write_csv(path: str, rows, columns) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def write_json(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def graph_results(out: str):
    """Per-graph JSON files already written in `out`, sorted by graph name."""
    names = sorted(f for f in os.listdir(out) if f.endswith(".json"))
    return [read_json(os.path.join(out, f)) for f in names]


def read_json(path: str, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def md_table(header, rows) -> str:
    def cell(x):
        return str(x).replace("|", "\\|")
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(cell(x) for x in r) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def fmt_distance(d: float) -> str:
    return "inf" if d == float("inf") else f"{d:.10g}"  # hides float noise such as 12.979999999
