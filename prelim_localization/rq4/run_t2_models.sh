#!/usr/bin/env bash
# T2 cross-backbone: run M0→M4 on S1 (n=57, file-given) for each open model via SiliconFlow API.
# No GPU, no Docker (coverage cached). Resumable: re-run to continue. Per-model results dir.
cd /Users/zt25/coding/localization_line/prelim_localization || exit 1
source .t2_secrets
export OPENAI_BASE_URL="$T2_BASE_URL" OPENAI_API_KEY="$T2_API_KEY"
export RQ4_PASSES_ONLY="passA_normal,passB_covnarrow"      # M0→M4 only (skip M5 pass)
export RQ4_WORKERS="${RQ4_WORKERS:-6}" RQ4_COV_WORKERS=2    # API concurrency (modest → avoid 429)
export RQ4_GIT_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo uncommitted)"
for M in $T2_MODELS; do
  tag=$(echo "$M" | tr '/' '_'); RD="rq4/results_${tag}"
  echo "===== $(date '+%T') T2 model: $M -> $RD ====="
  RQ4_RESULTS="$RD" MODEL="$M" python3 rq4/run_all.py --task e2e || { echo "!! e2e FAILED: $M"; continue; }
  RQ4_RESULTS="$RD" MODEL="$M" python3 rq4/run_all.py --task sig
  echo "----- $M done: $(python3 -c "import json;d=json.load(open('$RD/significance.json'));v=d['deltas']['M4_minus_M0']['R@10'];print('M4-M0 R@10 Δ=%spp CI=%s sig=%s'%(v['delta_pp'],v['ci95'],v['sig']))" 2>/dev/null) -----"
done
echo "===== $(date '+%T') ALL T2 MODELS DONE ====="
