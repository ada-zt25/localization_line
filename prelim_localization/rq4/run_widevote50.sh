#!/usr/bin/env bash
cd /Users/zt25/coding/localization_line/prelim_localization || exit 1
source .t2_secrets
export EGL_WIDE_VOTE=1 EGL_WIDE_MIN=45
for M in "tencent/Hunyuan-A13B-Instruct" "inclusionAI/Ling-flash-2.0"; do
  tag=$(echo "$M" | tr '/' '_'); D="rq4/results_${tag}"
  echo "===== $(date '+%T') $M passA FORCED-WIDE ====="
  OPENAI_BASE_URL="$T2_BASE_URL" OPENAI_API_KEY="$T2_API_KEY" MODEL="$M" SWEBENCH_DATASET=lite EGL_WIDE_VOTE=1 EGL_WIDE_MIN=45 \
    python3 egl_e2e.py --out "$D/passA_widevote.json" --k 5 --topk 10 --lines-cap 60 --workers 4 --cov-workers 2 --arise-gold \
    --instances "$D/S1_ids.json" --reuse-files "$D/oracle_files_S1.json" --dump-substrate > "$D/passA_widevote.log" 2>&1 || { echo "!!passA FAIL $M"; continue; }
  echo "===== $(date '+%T') $M passB FORCED-WIDE ====="
  OPENAI_BASE_URL="$T2_BASE_URL" OPENAI_API_KEY="$T2_API_KEY" MODEL="$M" SWEBENCH_DATASET=lite EGL_WIDE_VOTE=1 EGL_WIDE_MIN=45 \
    python3 egl_e2e.py --out "$D/passB_widevote.json" --k 5 --topk 10 --lines-cap 60 --workers 4 --cov-workers 2 --arise-gold \
    --cov-narrow --instances "$D/S1_ids.json" --reuse-files "$D/oracle_files_S1.json" --dump-substrate > "$D/passB_widevote.log" 2>&1 || { echo "!!passB FAIL $M"; continue; }
  echo "===== $(date '+%T') $M DONE ====="
done
echo "===== $(date '+%T') ALL FORCED-WIDE DONE ====="
