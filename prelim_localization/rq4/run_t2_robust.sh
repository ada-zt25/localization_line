#!/usr/bin/env bash
# Robust T2 driver: runs run_t2_models.sh at lower concurrency with a STALL WATCHDOG.
# If the log goes silent >6 min (transient SiliconFlow stall), kill the subtree and retry —
# the run is resumable per-instance, so it continues where it stopped. Exits on completion.
cd /Users/zt25/coding/localization_line/prelim_localization || exit 1
LOG=rq4/results/t2_run.log
STALL=360
for attempt in $(seq 1 30); do
  echo "=== ATTEMPT $attempt $(date '+%T') (workers=4) ===" >> "$LOG"
  RQ4_WORKERS=4 bash rq4/run_t2_models.sh >> "$LOG" 2>&1 &
  ORCH=$!
  while kill -0 $ORCH 2>/dev/null; do
    grep -q "ALL T2 MODELS DONE" "$LOG" && break
    now=$(date +%s); mt=$(stat -f %m "$LOG" 2>/dev/null || echo "$now")
    if [ $((now-mt)) -gt $STALL ]; then
      echo "!! STALL >${STALL}s at attempt $attempt — killing subtree, will resume" >> "$LOG"
      pkill -P $ORCH 2>/dev/null; kill $ORCH 2>/dev/null; pkill -f "egl_e2e.py" 2>/dev/null
      sleep 5; break
    fi
    sleep 30
  done
  wait $ORCH 2>/dev/null
  if grep -q "ALL T2 MODELS DONE" "$LOG"; then echo "=== T2 COMPLETE $(date '+%T') ===" >> "$LOG"; break; fi
done
