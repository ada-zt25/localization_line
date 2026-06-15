#!/usr/bin/env bash
# Unified PairCoder benchmark runner: FIVE models x FOUR libraries x ALL tasks x B0-B4 x N runs.
#
# The four libraries are UNSEEN/private by design (the research target): simplug is a
# vendored low-popularity real library; frameforge / keyvault / meshlink are private
# synthetic libraries authored in exec_oracle/ (zero model prior, no vendoring needed).
#
# Per library: anchor suite (oracle trustworthiness gate) -> generate (Ollama) -> execution-oracle eval.
#   - simplug uses its own pipeline (paircoder_step0_simplug_pilot.py + exec_oracle/run_exec_eval.py)
#   - frameforge / keyvault / meshlink use the generic harness (exec_oracle/benchlib_*.py)
# All four write result/<lib>_5model/exec_eval/exec_results.csv (with pair_type/difficulty),
# so one visualizer (visualize_benchmark.sh) handles them uniformly.
#
# Usage:
#   bash run_benchmark.sh                                  # 4 libs, 5 models, 3 runs (full)
#   RUNS=1 bash run_benchmark.sh                           # 1 run/condition (faster)
#   LIBS="frameforge" bash run_benchmark.sh                # one library
#   MODELS="qwen2.5:7b" RUNS=1 bash run_benchmark.sh       # quick smoke
#   TASKS="frameforge-F001,frameforge-F008" LIBS=frameforge bash run_benchmark.sh   # task subset (single lib)
#   CLEAN=1 bash run_benchmark.sh                          # wipe each lib's result dir first (fresh run)
#   PY=python3.14 bash run_benchmark.sh                    # pick the experiment interpreter
#
# Prerequisites:
#   - Ollama at http://localhost:11434 with all models pulled.
#   - frameforge / keyvault / meshlink are pure-Python private libs in exec_oracle/ -- no install.
#   - Only simplug uses vendored deps (exec_oracle/vendor: simplug/diot/inflection, already present);
#     run with the interpreter that can import them.
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$PWD"

PY="${PY:-python3}"
LIBS="${LIBS:-simplug diot simpleconf bidict glom}"
MODELS="${MODELS:-qwen2.5:7b,qwen2.5-coder:7b,llama3.1:8b,gemma2:9b,mistral:7b}"
METHODS="${METHODS:-B0_direct,B1_api_list,B2_raw_api_docs,B3_oracle_api_sequence,B4_gold_pair_rule}"
RUNS="${RUNS:-3}"
TEMPERATURE="${TEMPERATURE:-0.2}"
TASKS="${TASKS:-}"
RESULT_ROOT="${RESULT_ROOT:-$ROOT/result}"
CLEAN="${CLEAN:-0}"               # CLEAN=1 -> wipe each lib's result/<lib>_5model before running

echo "=================================================="
echo " PairCoder unified benchmark (4 libs x 5 models)"
echo "=================================================="
echo " libs    : $LIBS"
echo " models  : $MODELS"
echo " methods : $METHODS"
echo " runs    : $RUNS    temperature: $TEMPERATURE"
echo " python  : $PY  ($($PY --version 2>&1))"
echo " results : $RESULT_ROOT/<lib>_5model"
[ -n "$TASKS" ] && echo " tasks   : $TASKS (subset)"
echo "--------------------------------------------------"

command -v "$PY" >/dev/null 2>&1 || { echo "ERROR: PY='$PY' not found on PATH." >&2; exit 1; }
if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "ERROR: cannot reach Ollama at http://localhost:11434 (start it with: ollama serve)" >&2
  exit 1
fi

task_arg=()
[ -n "$TASKS" ] && task_arg=(--tasks "$TASKS")

run_simplug() {
  local rdir="$1"
  echo "--- [1/2] generate + static check (paircoder_step0_simplug_pilot.py) ---"
  "$PY" paircoder_step0_simplug_pilot.py \
    --models "$MODELS" --methods "$METHODS" --temperature "$TEMPERATURE" \
    --runs "$RUNS" --result-dir "$rdir" ${task_arg[@]+"${task_arg[@]}"}
  echo "--- [2/2] anchor gate + execution-oracle eval (run_exec_eval.py) ---"
  ( cd exec_oracle && "$PY" run_exec_eval.py --result-dir "$rdir" )
}

run_generic() {
  local lib="$1" rdir="$2"
  ( cd exec_oracle
    echo "--- [1/3] anchor suite (oracle trustworthiness gate) ---"
    "$PY" benchlib.py "$lib"
    echo "--- [2/3] generate (Ollama, B0-B4) ---"
    "$PY" benchlib_generate.py --lib "$lib" --models "$MODELS" --methods "$METHODS" \
      --temperature "$TEMPERATURE" --runs "$RUNS" --result-dir "$rdir" ${task_arg[@]+"${task_arg[@]}"}
    echo "--- [3/3] execution-oracle eval ---"
    "$PY" benchlib_eval.py --result-dir "$rdir" )
}

for lib in $LIBS; do
  rdir="$RESULT_ROOT/${lib}_5model"
  echo ""; echo "########## $lib  ->  $rdir ##########"
  if [ "$CLEAN" = "1" ] && [ -d "$rdir" ]; then
    echo "--- CLEAN=1: wiping $rdir ---"
    rm -rf "$rdir"
  fi
  if [ "$lib" = "simplug" ]; then
    run_simplug "$rdir"
  else
    run_generic "$lib" "$rdir"
  fi
done

echo ""
echo "=================================================="
echo " Done. Per-lib summaries: <result>/exec_eval/exec_summary.md"
echo " Visualize all libs with:  bash visualize_benchmark.sh"
echo "=================================================="
