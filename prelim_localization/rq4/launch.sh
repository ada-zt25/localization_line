#!/usr/bin/env bash
# RQ4 anti-disconnect launcher (run ON the A800 box). The whole sequence runs under tmux so it SURVIVES
# SSH drops; every sub-run is resumable (re-running this script continues where it stopped). A heartbeat
# writes one-line STATUS every 30s so you can monitor over ONE persistent connection — never reconnect-
# spam the gateway. The LLM calls hit the LOCAL vLLM (no tunnel in the hot path), so a dropped tunnel
# does NOT touch the experiment.
set -uo pipefail
cd "$(cd "$(dirname "$0")/.." && pwd)"          # -> prelim_localization
SESS=rq4
LOG="$PWD/rq4/results/run.log"
STATUS="$PWD/rq4/results/STATUS.txt"
mkdir -p rq4/results
: "${MODEL:=Qwen2.5-Coder-32B-Instruct}"
: "${OPENAI_BASE_URL:=http://127.0.0.1:8000/v1}"
export MODEL OPENAI_BASE_URL SWEBENCH_DATASET=lite
export PATH="/root/miniconda3/bin:$PATH"        # tmux shell is non-login → ensure conda python on PATH

if [ "${1:-}" = "--inner" ]; then               # the actual work (runs inside tmux)
  ( while true; do
      echo "$(date '+%F %T') | $(tail -n1 "$LOG" 2>/dev/null | cut -c1-160)" > "$STATUS"; sleep 30
    done ) &                                     # heartbeat (dies with the tmux window)
  HB=$!; trap 'kill $HB 2>/dev/null' EXIT
  echo "==== RQ4 START $(date) | file-given | MODEL=$MODEL BASE_URL=$OPENAI_BASE_URL ===="
  # file-given main path: e2e(oracle gold file) → sig → verify. (Task1 file-loc is OPTIONAL, run separately.)
  python rq4/run_all.py --task e2e \
    && python rq4/run_all.py --task sig \
    && python rq4/run_all.py --verify
  rc=$?
  echo "==== RQ4 DONE $(date) rc=$rc ===="
  echo "DONE rc=$rc $(date)" > "$PWD/rq4/results/DONE.txt"
  exit $rc
fi

# launcher side
if tmux has-session -t "$SESS" 2>/dev/null; then
  echo "tmux '$SESS' already running (resumable)."
else
  tmux new-session -d -s "$SESS" "bash '$0' --inner 2>&1 | tee -a '$LOG'"
  echo "launched tmux '$SESS'."
fi
cat <<EOF
monitor (use ONE ssh, do NOT reconnect-spam):
  cat   $STATUS      # one-line heartbeat (updates every 30s)
  tail -f $LOG       # full streaming log
  tmux attach -t $SESS   # attach the live session (Ctrl-b d to detach)
results land in: rq4/results/  (lineloc_e2e.json, significance.json, fileloc_sweep.json)
done marker:    rq4/results/DONE.txt
EOF
