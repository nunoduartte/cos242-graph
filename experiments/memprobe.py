"""Process memory probes for the memory experiments (Linux /proc).

Peak RSS is read from the kernel's high-water mark (VmHWM), not sampled: it is
reset just before the measured block (writing "5" to /proc/self/clear_refs,
Linux >= 4.0), so after the block VmHWM is the largest RSS reached inside it,
even if that memory was already freed by the end. When the reset is not
allowed, a sampling thread (every 5 ms) is used instead and the record says so;
sampling can miss short spikes.

What RSS measures: resident pages of the whole process, including the Python
interpreter, the graph, the allocator's free lists and memory the algorithm
already released but the allocator kept. The increase over the block is
therefore an approximation of the extra memory of the algorithm, not the exact
size of its data structures.
"""
import json
import subprocess
import sys
import threading
import time
from contextlib import contextmanager


def _status_kb(field: str) -> int:
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith(field + ":"):
                return int(line.split()[1])
    raise RuntimeError(f"{field} not found in /proc/self/status")


def rss_mb() -> float:
    return _status_kb("VmRSS") / 1024


def hwm_mb() -> float:
    """Peak RSS since the process started or the last reset_peak()."""
    return _status_kb("VmHWM") / 1024


def reset_peak() -> bool:
    """Resets VmHWM to the current RSS; False if the kernel does not allow it."""
    try:
        with open("/proc/self/clear_refs", "w") as f:
            f.write("5")
    except OSError:
        return False
    return hwm_mb() <= rss_mb() + 1  # it really went down to the current RSS


class _Sampler(threading.Thread):
    def __init__(self, interval):
        super().__init__(daemon=True)
        self.interval, self.peak, self._done = interval, rss_mb(), threading.Event()

    def run(self):
        while not self._done.wait(self.interval):
            self.peak = max(self.peak, rss_mb())

    def stop(self):
        self._done.set()
        self.join()
        self.peak = max(self.peak, rss_mb())


@contextmanager
def peak_rss(record: dict, prefix: str = ""):
    """Fills record with <prefix>rss_before_mb, rss_after_mb, peak_rss_mb,
    peak_increase_mb and peak_method for the enclosed block. The values are
    filled even if the block raises (e.g. a timeout: the peak up to that point)."""
    before = rss_mb()
    exact = reset_peak()
    sampler = None if exact else _Sampler(0.005)
    if sampler:
        sampler.start()
    try:
        yield record
    finally:
        if sampler:
            sampler.stop()
        peak = hwm_mb() if exact else sampler.peak
        record.update({f"{prefix}rss_before_mb": before, f"{prefix}rss_after_mb": rss_mb(),
                       f"{prefix}peak_rss_mb": peak, f"{prefix}peak_increase_mb": peak - before,
                       f"{prefix}peak_method": "VmHWM after clear_refs" if exact else "sampling every 5 ms"})


def run_worker(module: str, args, timeout: float, max_memory_gb: float = 0) -> dict:
    """Runs `python -m module --worker ...args` in a new process and returns the
    JSON it prints on its last stdout line. A crash, a kill or a memory error
    becomes a record with the status instead of an exception."""
    def limit_memory():
        if max_memory_gb:
            import resource
            limit = int(max_memory_gb * 2**30)
            resource.setrlimit(resource.RLIMIT_AS, (limit, limit))

    cmd = [sys.executable, "-m", module, "--worker", *map(str, args)]
    t = time.perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              preexec_fn=limit_memory if max_memory_gb else None)
    except subprocess.TimeoutExpired:
        return {"status": f"killed: process exceeded {timeout:.0f} s (no measurements)",
                "process_s": time.perf_counter() - t}
    lines = proc.stdout.strip().splitlines()
    try:
        record = json.loads(lines[-1])
    except (IndexError, json.JSONDecodeError):
        err = proc.stderr.strip().splitlines()
        record = {"status": f"failed (exit {proc.returncode}): {err[-1] if err else 'no output'}"}
    record["process_s"] = time.perf_counter() - t
    return record


def emit(record: dict) -> None:
    """Worker side of run_worker: the result as one JSON line."""
    sys.stdout.write(json.dumps(record, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def clean_baseline() -> float:
    """RSS after a full collection, the reference point of a worker."""
    import gc
    gc.collect()
    return rss_mb()

