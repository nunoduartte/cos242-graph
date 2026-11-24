#!/usr/bin/env bash
# Official Part 3 runs, in the order used for the report (one heavy experiment at a time).
# Every step is resumable: run the same step again and it continues (--resume) without
# repeating finished rounds. Logs: results/part3/logs/.
#
#   experiments/part3/official_runs.sh STEP
#   STEP: study1 | study3-bf | study3-fw-small | study3-fw-w2 | study2 | study4-sub | study4-sub-numba
#         | study4-official | report | consistency
#
# PY must have NumPy and Numba for the Floyd-Warshall steps (engine numba); see README.
set -euo pipefail
cd "$(dirname "$0")/../.."
PY=${PY:-$HOME/.venvs/cos242-accel/bin/python}
D=${D:-$HOME/Downloads/graphs}
LOG=results/part3/logs
mkdir -p "$LOG"

# Study 3: the same settings on every call (the --resume check compares them per graph).
BENCH=(--data-dir "$D" --rounds 10 --run-timeout 3600 --budget 14400 --max-memory-gb 16
       --fw-engine numba --fw-workers 16 --fw-timeout-for grafo_W_2=14400 --fw-budget-for grafo_W_2=0 --resume)

case "${1:-}" in
  study1)            $PY run.py part3-bellman-ford --data-dir "$D" --timeout 3600 ;;
  study3-bf)         $PY run.py part3-benchmark "${BENCH[@]}" --algorithms bellman-ford ;;
  study3-fw-small)   $PY run.py part3-benchmark "${BENCH[@]}" --algorithms floyd-warshall \
                         --graphs grafo_W_1 grafo_W_3 grafo_W_4 grafo_W_5 ;;
  study3-fw-w2)      $PY run.py part3-benchmark "${BENCH[@]}" --algorithms floyd-warshall --graphs grafo_W_2 ;;
  study2)            $PY run.py part3-floyd-warshall --data-dir "$D" --from-benchmark results/part3/benchmark \
                         --fw-engine numba --fw-workers 16 --timeout 14400 ;;
  # Study 4, equal implementation level: both algorithms in pure Python, one process.
  study4-sub)        $PY run.py part3-all-pairs --data-dir "$D" --graphs --rounds 10 \
                         --subgraphs grafo_W_2:500,1000,2000,3000,4000 \
                         --fw-engine python --fw-workers 1 --run-timeout 3600 --budget 14400 --resume ;;
  # Same subgraphs, Floyd-Warshall with the engine of the official graphs (Numba, 16 threads).
  study4-sub-numba)  $PY run.py part3-all-pairs --data-dir "$D" --graphs --rounds 10 \
                         --subgraphs grafo_W_2:500,1000,2000,3000,4000 --algorithms floyd-warshall \
                         --fw-engine numba --fw-workers 16 --out results/part3/all_pairs_numba --resume ;;
  # Official graphs: Floyd-Warshall rounds taken from study 3; all-pairs Bellman-Ford measured here.
  study4-official)   $PY run.py part3-all-pairs --data-dir "$D" --graphs grafo_W_1 grafo_W_2 --subgraphs \
                         --rounds 10 --fw-engine numba --fw-workers 16 --fw-from-benchmark results/part3/benchmark \
                         --run-timeout 3600 --budget 14400 \
                         --timeout-for grafo_W_2=${BF_W2_TIMEOUT:-14400} --budget-for grafo_W_2=${BF_W2_BUDGET:-86400} \
                         --resume ;;
  report)            $PY run.py part3-report ;;
  consistency)       $PY run.py part3-consistency --data-dir "$D" ;;
  *) sed -n 2,10p "$0"; exit 2 ;;
esac
