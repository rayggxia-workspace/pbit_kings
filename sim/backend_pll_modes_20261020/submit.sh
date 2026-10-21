#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export MODE_ROOT="$ROOT" MODE_CASES="${1:-all}" PYTHON_BIN="${PYTHON_BIN:-python3}" CORNER="${CORNER:-WC}"
export MODE_CORNER="$CORNER"
export CPUS="${CPUS:-4}" MEM="${MEM:-8G}" TIME_LIMIT="${TIME_LIMIT:-0}"
export DIAG_DEBUG="${DIAG_DEBUG:-minimal}" MAX_WALL_HOURS="${MAX_WALL_HOURS:-0}"
export INPUT_DIR="${INPUT_DIR:-$(dirname "$ROOT")/backend_inputs_261014}"
export CHECK_JOB="${CHECK_JOB:-$(dirname "$ROOT")/backend_fast_20261018/results/38117744}"
export BUILD_JOB="${BUILD_JOB:-}"
export PREVIOUS_RESULT="${PREVIOUS_RESULT:-}"
"$PYTHON_BIN" "$ROOT/run.py" verify "$ROOT"
"$PYTHON_BIN" "$ROOT/run.py" validate "$MODE_CASES" "$CORNER"
[[ "$CPUS" =~ ^[1-9][0-9]*$ ]] || exit 2
mkdir -p "$ROOT/logs"
export MODE_SNAPSHOT
MODE_SNAPSHOT="$("$PYTHON_BIN" "$ROOT/package.py" snapshot "$ROOT")"
echo "PLL_MODE_CASES=$MODE_CASES CORNER=$CORNER CPUS=$CPUS MEM=$MEM ordinary_serial_VCS=1"
sbatch --partition="${PARTITION:-v6_384}" --nodes=1 --ntasks=1 --cpus-per-task="$CPUS" \
  --mem="$MEM" --time="$TIME_LIMIT" --job-name=chi_modes --export=ALL \
  --output="$ROOT/logs/job-%j.out" --error="$ROOT/logs/job-%j.err" "$MODE_SNAPSHOT/run_sbatch.sh"
