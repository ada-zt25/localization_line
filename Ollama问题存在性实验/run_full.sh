#!/usr/bin/env bash
# FULL experiment: the real low-popularity libraries with genuine pairwise
# composition constraints (simplug + diot + simpleconf + bidict + glom), 5 models,
# B0-B4, 3 runs. (pyparam was dropped: its add_param/parse/ns.attr semantics are
# fully conveyed by a plain API list -- B1 saturates and B4-B1 ~= 0, no gap to test;
# bidict + glom were added as new genuine-composition libs. See docs/工作进程.md.)
# NOTE: simplug runs via its own pilot harness, not this benchlib runner.
#
# Per lib: anchor gate -> generate (Ollama) -> execution-oracle eval. Results in
# result/<lib>_5model/exec_eval/ ; visualize with: bash visualize_benchmark.sh
#
# Thin wrapper over run_benchmark.sh (the engine). For a fast sanity check first
# use run_quicktest.sh.
#
# Usage:
#   bash run_full.sh
#   CLEAN=1 bash run_full.sh                 # wipe result dirs first
#   RUNS=5 bash run_full.sh                  # tighter estimates
set -euo pipefail
cd "$(dirname "$0")"

export LIBS="${LIBS:-simplug diot simpleconf glom bidict}"
export MODELS="${MODELS:-qwen2.5:7b,qwen2.5-coder:7b,llama3.1:8b,gemma2:9b,mistral:7b}"
export METHODS="${METHODS:-B0_direct,B1_api_list,B2_raw_api_docs,B3_oracle_api_sequence,B4_gold_pair_rule}"
export RUNS="${RUNS:-3}"

echo ">> FULL experiment: 5 libs x 5 models x B0-B4 x ${RUNS} runs"
exec bash run_benchmark.sh
