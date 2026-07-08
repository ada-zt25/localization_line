#!/usr/bin/env bash
# Robust wrapper for run_t3t6.sh: stall watchdog (kill+resume if log silent >6 min), up to 30 attempts.
cd /Users/zt25/coding/localization_line/prelim_localization || exit 1
LOG=rq4/results/t3t6_run.log
STALL=360
for attempt in $(seq 1 30); do
  echo "=== ATTEMPT $attempt $(date '+%T') (workers=4) ===" >> "$LOG"
  RQ4_WORKERS=4 bash rq4/run_t3t6.sh >> "$LOG" 2>&1 &
  P=$!
  while kill -0 $P 2>/dev/null; do
    grep -q "ALL T3/T6 DONE" "$LOG" && break
    now=$(date +%s); mt=$(stat -f %m "$LOG" 2>/dev/null || echo "$now")
    if [ $((now-mt)) -gt $STALL ]; then
      echo "!! STALL >${STALL}s attempt $attempt — killing, will resume" >> "$LOG"
      pkill -P $P 2>/dev/null; kill $P 2>/dev/null; pkill -f "egl_e2e.py" 2>/dev/null; sleep 5; break
    fi
    sleep 30
  done
  wait $P 2>/dev/null
  grep -q "ALL T3/T6 DONE" "$LOG" && { echo "=== T3/T6 COMPLETE $(date '+%T') ===" >> "$LOG"; break; }
done
