#!/usr/bin/env bash
# Started once by hand: waits for the W_2 Floyd-Warshall benchmark (pid given) and then runs the
# remaining official steps one after the other, never two at the same time.
cd "$(dirname "$0")/../../.."
while kill -0 "$1" 2>/dev/null; do sleep 30; done
echo "[$(date +%T)] W_2 benchmark finished; starting the chain"
for step in study2 study4-sub study4-sub-numba study4-official consistency; do
  echo "[$(date +%T)] start $step"
  experiments/part3/official_runs.sh "$step" > "results/part3/logs/$step.log" 2>&1
  echo "[$(date +%T)] end $step (exit $?)"
done
echo "[$(date +%T)] chain done"
