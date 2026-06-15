#!/usr/bin/env bash
# QUICK method-effectiveness test on the new REAL low-popularity libraries
# (diot / simpleconf). Fast sanity check: does injecting the extracted
# gold pair rules (B4) beat the bare baseline (B0) on these unseen libs?
#
#   - libs   : diot simpleconf   (NOT simplug; that's the pilot. pyparam dropped:
#              weak benchmark, see docs/工作进程.md 6.15)
#   - models : 2 by default (override with MODELS=...)
#   - methods: B0_direct vs B4_gold_pair_rule only
#   - runs   : 1
#
# Thin wrapper over run_benchmark.sh (the engine). For the complete study use run_full.sh.
#
# Usage:
#   bash run_quicktest.sh
#   LIBS="diot" MODELS="qwen2.5:7b" bash run_quicktest.sh     # even faster (one lib/model)
#   METHODS="B0_direct,B1_api_list,B4_gold_pair_rule" bash run_quicktest.sh
set -euo pipefail
cd "$(dirname "$0")"

export LIBS="${LIBS:-diot simpleconf}"
export MODELS="${MODELS:-qwen2.5:7b,qwen2.5-coder:7b}"
export METHODS="${METHODS:-B0_direct,B4_gold_pair_rule}"
export RUNS="${RUNS:-1}"
export CLEAN="${CLEAN:-1}"          # fresh result dirs for a clean quick read

echo ">> QUICK test: B0 vs B4 on $LIBS (models=$MODELS, runs=$RUNS)"
exec bash run_benchmark.sh
