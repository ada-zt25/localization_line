#!/usr/bin/env bash
# Run the 5-model pair-composition comparison (multi-task, multi-round).
#
# The five edge/mid-size (7-9B) models, across four vendors:
#   qwen2.5:7b        (Alibaba, general)
#   qwen2.5-coder:7b  (Alibaba, code)     <- general-vs-code controlled pair
#   llama3.1:8b       (Meta,    general)
#   gemma2:9b         (Google,  general)
#   mistral:7b        (Mistral, general)
#
# Each (model x task x method) is run RUNS times; the summary aggregates with
# majority vote across runs (see paircoder_step0_simplug_pilot.py::summarize).
#
# Usage:
#   bash run_comparison.sh                 # defaults below (5 models, 3 runs)
#   RUNS=5 bash run_comparison.sh          # more rounds for tighter estimates
#   RUNS=1 bash run_comparison.sh          # quick smoke test
#   KEEP_OLD=1 bash run_comparison.sh      # do NOT wipe the result dir first
#   PYTHON=python bash run_comparison.sh   # use a specific interpreter (e.g. conda's)
#
# Prerequisites:
#   - Ollama running locally (http://localhost:11434)
#   - All five models pulled (see `ollama list`)
#   - The visualization step needs matplotlib; the experiment step does not.
#     Set PYTHON to the interpreter that has matplotlib (often conda's `python`)
#     so the run and the later plots use the same environment.
set -euo pipefail

cd "$(dirname "$0")"

# Interpreter used for both the experiment and the suggested visualization step.
# Defaults to python3, but set PYTHON=python to use conda's interpreter, etc.
PYTHON="${PYTHON:-python3}"

MODELS="${MODELS:-qwen2.5:7b,qwen2.5-coder:7b,llama3.1:8b,gemma2:9b,mistral:7b}"
METHODS="${METHODS:-B0_direct,B1_api_list,B2_raw_api_docs,B3_oracle_api_sequence,B4_gold_pair_rule}"
TEMPERATURE="${TEMPERATURE:-0.2}"
RUNS="${RUNS:-3}"
RESULT_DIR="${RESULT_DIR:-result/simplug_7b_5model_comparison}"
KEEP_OLD="${KEEP_OLD:-0}"

echo "=================================================="
echo " PairCoder 5-model x method comparison"
echo "=================================================="
echo " models      : $MODELS"
echo " methods     : $METHODS"
echo " temperature : $TEMPERATURE"
echo " runs/cond   : $RUNS  (majority vote across runs)"
echo " result dir  : $RESULT_DIR"
echo " python      : $PYTHON"
echo "--------------------------------------------------"

# Make sure the chosen interpreter actually exists.
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "ERROR: PYTHON='$PYTHON' not found on PATH." >&2
  echo "       Try: PYTHON=python3 bash run_comparison.sh" >&2
  exit 1
fi

# Quick check that ollama is reachable before spending time.
if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "ERROR: cannot reach Ollama at http://localhost:11434" >&2
  echo "       Start it with:  ollama serve" >&2
  exit 1
fi

# Start from a clean result dir so ONLY the latest 5-model results remain,
# unless the caller explicitly asks to keep old files (KEEP_OLD=1).
if [ "$KEEP_OLD" != "1" ] && [ -d "$RESULT_DIR" ]; then
  echo "Wiping existing result dir for a clean run: $RESULT_DIR"
  rm -rf "$RESULT_DIR"
fi

"$PYTHON" paircoder_step0_simplug_pilot.py \
  --models "$MODELS" \
  --methods "$METHODS" \
  --temperature "$TEMPERATURE" \
  --runs "$RUNS" \
  --result-dir "$RESULT_DIR"

echo "--------------------------------------------------"
echo "Done. Results written to: $RESULT_DIR"
echo "Now visualize with:"
echo "  $PYTHON visualize_results.py --result-dir \"$RESULT_DIR\""
