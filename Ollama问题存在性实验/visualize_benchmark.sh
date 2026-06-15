#!/usr/bin/env bash
# Render execution-oracle figures for every result dir that has exec_eval/exec_results.csv
# (works for msgspec/peewee/niquests AND simplug -- all write the same CSV with
# pair_type/difficulty columns). Figures: pass-by-method, method x model,
# method x pair_type, method x difficulty, outcome breakdown + charts_summary.md.
#
# Visualization only reads CSV/JSON (it does NOT import the vendored libs), so run it
# with whatever interpreter has matplotlib -- typically conda's python.
#
# Usage:
#   bash visualize_benchmark.sh                                   # all result dirs
#   VIZ_PY=python bash visualize_benchmark.sh                     # use conda's python (has matplotlib)
#   DIRS="result/msgspec_5model result/peewee_5model" bash visualize_benchmark.sh
#   METRIC=run bash visualize_benchmark.sh                        # per-run instead of task-majority
set -euo pipefail
cd "$(dirname "$0")"

VIZ_PY="${VIZ_PY:-python3}"
METRIC="${METRIC:-task}"
RESULT_ROOT="${RESULT_ROOT:-$PWD/result}"
DIRS="${DIRS:-}"

command -v "$VIZ_PY" >/dev/null 2>&1 || { echo "ERROR: VIZ_PY='$VIZ_PY' not found." >&2; exit 1; }
if ! "$VIZ_PY" -c "import matplotlib" >/dev/null 2>&1; then
  echo "ERROR: '$VIZ_PY' has no matplotlib. Use a matplotlib interpreter, e.g. VIZ_PY=python (conda)." >&2
  echo "       or:  $VIZ_PY -m pip install matplotlib" >&2
  exit 1
fi

# Build a space-SAFE list of result dirs. Auto-discovered absolute paths may
# contain spaces (e.g. this repo's path), so iterate newline-delimited, not via
# word-splitting `for d in $DIRS` (which would break on the spaces).
DIR_LIST=()
if [ -n "$DIRS" ]; then
  # user-provided, space-separated (pass paths WITHOUT spaces, e.g. result/msgspec_5model)
  for d in $DIRS; do DIR_LIST+=("$d"); done
else
  while IFS= read -r d; do
    [ -n "$d" ] && DIR_LIST+=("$d")
  done < <(find "$RESULT_ROOT" -maxdepth 3 -type f -name exec_results.csv -exec dirname {} \; 2>/dev/null \
           | sed 's#/exec_eval$##' | sort -u)
fi

if [ "${#DIR_LIST[@]}" -eq 0 ]; then
  echo "No result dirs with exec_eval/exec_results.csv under $RESULT_ROOT." >&2; exit 1
fi

for d in "${DIR_LIST[@]}"; do
  if [ -f "$d/exec_eval/exec_results.csv" ]; then
    echo "=== visualize: $d (metric=$METRIC) ==="
    "$VIZ_PY" visualize_exec.py --result-dir "$d" --metric "$METRIC"
  else
    echo "skip (no exec_results.csv): $d"
  fi
done

echo ""
echo "Figures written under each <result>/exec_eval/figs/."
