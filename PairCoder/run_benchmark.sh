#!/usr/bin/env bash
# Unified PairCoder benchmark runner: FIVE models x SIX libraries x ALL tasks x B0-B4 x N runs.
#
# All six libraries are REAL, vendored, low-popularity/unseen by design (the research target),
# and run uniformly on the generic benchlib harness (exec_oracle/lib_<name>.py + benchlib_*.py):
#   simplug 0.5.7 (plugin) | diot 0.3.4 (attr-dict) | python-simpleconf 0.9.3 (config)
#   glom 25.x (extraction) | bidict 0.23.x (bimap, high-prior control)
#   sqlitedict 2.1.0 (persistent store; supplies the completion-obligation pair class)
#
# Per library: anchor suite (oracle trustworthiness gate) -> generate (Ollama) -> execution-oracle eval.
# Each writes result/<lib>_5model/exec_eval/exec_results.csv (with pair_type/difficulty),
# so one visualizer (visualize_benchmark.sh) handles them uniformly.
#
# Usage:
#   bash run_benchmark.sh                                  # 6 libs, 5 models, 3 runs (full)
#   RUNS=1 bash run_benchmark.sh                           # 1 run/condition (faster)
#   LIBS="sqlitedict" bash run_benchmark.sh                # one library
#   MODELS="qwen2.5:7b" RUNS=1 bash run_benchmark.sh       # quick smoke
#   TASKS="glom-G001,glom-G008" LIBS=glom bash run_benchmark.sh   # task subset (single lib)
#   CLEAN=1 bash run_benchmark.sh                          # wipe each lib's result dir first (fresh run)
#   PY=python3.14 bash run_benchmark.sh                    # pick the experiment interpreter
#
# Prerequisites:
#   - Ollama at http://localhost:11434 with all models pulled.
#   - exec_oracle/vendor/ holds the six vendored libraries (+deps); rebuild per
#     PairCoder_Benchmark.md if missing. Use the interpreter that can import them.
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$PWD"

PY="${PY:-python3}"
LIBS="${LIBS:-simplug diot simpleconf bidict glom sqlitedict}"
MODELS="${MODELS:-qwen2.5:7b,qwen2.5-coder:7b,llama3.1:8b,gemma2:9b,mistral:7b}"
METHODS="${METHODS:-B0_direct,B1_api_list,B2_raw_api_docs,B3_oracle_api_sequence,B4_gold_pair_rule}"
RUNS="${RUNS:-1}"
TEMPERATURE="${TEMPERATURE:-0.2}"
TASKS="${TASKS:-}"
RESULT_ROOT="${RESULT_ROOT:-$ROOT/result}"
CLEAN="${CLEAN:-0}"               # CLEAN=1 -> wipe each lib's result/<lib>_5model before running
GEN_JOBS="${GEN_JOBS:-4}"
EVAL_JOBS="${EVAL_JOBS:-8}"
KEEP_ALIVE="${KEEP_ALIVE:-1h}"
NUM_PREDICT="${NUM_PREDICT:-500}"
TOP_P="${TOP_P:-0.9}"
NUM_GPU="${NUM_GPU:-}"

# Resolve a WORKING Python before the banner. On some Windows setups `python3` is
# a non-functional Microsoft Store shim, so fall back to `python` if it can't run.
if ! "$PY" -c "import sys" >/dev/null 2>&1; then
  if command -v python >/dev/null 2>&1 && python -c "import sys" >/dev/null 2>&1; then
    PY=python
  else
    echo "ERROR: no working Python (tried '$PY' and 'python'). Set PY=<your python>." >&2
    exit 1
  fi
fi

echo "=================================================="
echo " PairCoder unified benchmark (6 libs x 5 models)"
echo "=================================================="
echo " libs    : $LIBS"
echo " models  : $MODELS"
echo " methods : $METHODS"
echo " runs    : $RUNS    temperature: $TEMPERATURE"
echo " gen jobs: $GEN_JOBS    eval jobs: $EVAL_JOBS"
echo " keep-alive: $KEEP_ALIVE  num_predict: $NUM_PREDICT  top_p: $TOP_P"
[ -n "$NUM_GPU" ] && echo " num_gpu : $NUM_GPU"
echo " python  : $PY  ($($PY --version 2>&1))"
echo " results : $RESULT_ROOT/<lib>_5model"
[ -n "$TASKS" ] && echo " tasks   : $TASKS (subset)"
echo "--------------------------------------------------"

if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "ERROR: cannot reach Ollama at http://localhost:11434 (start it with: ollama serve)" >&2
  exit 1
fi

task_arg=()
[ -n "$TASKS" ] && task_arg=(--tasks "$TASKS")

num_gpu_arg=()
[ -n "$NUM_GPU" ] && num_gpu_arg=(--num-gpu "$NUM_GPU")

run_lib() {
  local lib="$1" rdir="$2"
  ( cd exec_oracle
    echo "--- [1/3] anchor suite (oracle trustworthiness gate) ---"
    "$PY" benchlib.py "$lib"
    echo "--- [2/3] generate one-shot conditions (Ollama, B0-B4) ---"
    "$PY" benchlib_generate.py --lib "$lib" --models "$MODELS" --methods "$METHODS" \
      --temperature "$TEMPERATURE" --runs "$RUNS" --jobs "$GEN_JOBS" --keep-alive "$KEEP_ALIVE" \
      --num-predict "$NUM_PREDICT" --top-p "$TOP_P" ${num_gpu_arg[@]+"${num_gpu_arg[@]}"} \
      --result-dir "$rdir" ${task_arg[@]+"${task_arg[@]}"}
    # Honest, leakage-free B5 is produced separately by fair_loop.py (dev/held input
    # split, equal budget K). The leaky b5_loop_run.py driver was removed by design.
    echo "--- [3/3] execution-oracle eval (B0-B4) ---"
    "$PY" benchlib_eval.py --result-dir "$rdir" --jobs "$EVAL_JOBS" )
}

for lib in $LIBS; do
  rdir="$RESULT_ROOT/${lib}_5model"
  echo ""; echo "########## $lib  ->  $rdir ##########"
  if [ "$CLEAN" = "1" ] && [ -d "$rdir" ]; then
    echo "--- CLEAN=1: wiping $rdir ---"
    rm -rf "$rdir"
  fi
  run_lib "$lib" "$rdir"
done

echo ""
echo "=================================================="
echo " Done. Per-lib summaries: <result>/exec_eval/exec_summary.md"
echo " Visualize all libs with:  bash visualize_benchmark.sh"
echo "=================================================="
