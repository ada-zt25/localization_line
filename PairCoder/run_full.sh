#!/usr/bin/env bash
# FULL experiment: the six real low-popularity libraries with genuine pairwise
# composition constraints (simplug + diot + simpleconf + bidict + glom + sqlitedict),
# 5 models, conditions B0-B4 (one-shot), 1 run/condition. All six run uniformly on
# the benchlib harness. (Honest, leakage-free B5 comes separately from
# exec_oracle/fair_loop.py -- dev/held split, equal budget K; the old leaky
# b5_loop_run.py driver was removed.)
# (sqlitedict supplies the completion-obligation pair class; pyparam was dropped --
# its add_param/parse/ns.attr semantics saturate B1 with no B4-B1 gap. See docs/工作进程.md.)
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

export LIBS="${LIBS:-simplug diot simpleconf glom bidict sqlitedict}"
export MODELS="${MODELS:-qwen2.5:7b,qwen2.5-coder:7b,llama3.1:8b,gemma2:9b,mistral:7b}"
export METHODS="${METHODS:-B0_direct,B1_api_list,B2_raw_api_docs,B3_oracle_api_sequence,B4_gold_pair_rule}"
export RUNS="${RUNS:-1}"

echo ">> FULL experiment: 6 libs x 5 models x B0-B4 (one-shot) x ${RUNS} run  (B5 via fair_loop.py, run separately)"
exec bash run_benchmark.sh
