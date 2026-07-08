#!/usr/bin/env bash
# T3 (pipeline off-path S3 + blended) + T6 (M5 assert-rerank) across the 3 T2 open backbones via
# SiliconFlow API. No GPU, no Docker (S1+S3 coverage cached). Resumable. Pairs with T2's S1 M0-M4.
cd /Users/zt25/coding/localization_line/prelim_localization || exit 1
source .t2_secrets
export OPENAI_BASE_URL="$T2_BASE_URL" OPENAI_API_KEY="$T2_API_KEY"
export SWEBENCH_DATASET=lite                                   # direct egl_e2e S3 calls need this (load_rows defaults to 'verified')
export RQ4_WORKERS="${RQ4_WORKERS:-4}" RQ4_COV_WORKERS=2
export RQ4_GIT_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo uncommitted)"
for M in $T2_MODELS; do
  tag=$(echo "$M" | tr '/' '_'); RD="rq4/results_${tag}"
  echo "===== $(date '+%T') T3/T6 model: $M -> $RD ====="
  # --- T6: add M5 (passC) on S1; passA/passB already done in RD from T2 (skipped) ---
  RQ4_RESULTS="$RD" MODEL="$M" RQ4_PASSES_ONLY="passA_normal,passB_covnarrow,passC_m5" \
    python3 rq4/run_all.py --task e2e || { echo "!! e2e(M5) FAILED $M"; }
  RQ4_RESULTS="$RD" MODEL="$M" RQ4_PASSES_ONLY="passA_normal,passB_covnarrow,passC_m5" \
    python3 rq4/run_all.py --task sig || true
  # --- T3: off-path S3 pipeline (M0=passA_S3 ours_static, M4=passB_S3 ours_dynamic) ---
  for spec in "passA_S3:--coverage --dump-substrate" "passB_S3:--cov-narrow --dump-substrate"; do
    name="${spec%%:*}"; flags="${spec#*:}"
    [ -f "$RD/${name}.json" ] && python3 -c "import json,sys; sys.exit(0 if 'summary' in json.load(open('$RD/${name}.json')) else 1)" 2>/dev/null && { echo "skip done: ${name}"; continue; }
    MODEL="$M" python3 egl_e2e.py --out "$RD/${name}.json" --k 5 --topk 10 --workers "$RQ4_WORKERS" --cov-workers 2 \
      --arise-gold --instances rq4/results/S3_ids.json --reuse-files rq4/results/oracle_files_S3.json $flags \
      || echo "!! S3 ${name} FAILED $M"
  done
  echo "----- $M done T3/T6 -----"
done
echo "===== $(date '+%T') ALL T3/T6 DONE ====="
