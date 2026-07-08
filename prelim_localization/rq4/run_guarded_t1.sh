#!/usr/bin/env bash
# Guarded T1 resume: workers=1 + disk watchdog. Aborts cleanly before host disk gets dangerous
# (Docker.raw can't be compacted on this Mac, so we cap risk instead). Resumable: re-run to continue.
cd /Users/zt25/coding/localization_line/prelim_localization || exit 1
LOG=rq4/results/t1_resume.log
RAW=~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw
FLOOR_MB=2560                       # abort if host free drops below 2.5 GB
RQ4_GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo uncommitted) \
  python3 rq4/relabel_t1.py --workers 1 > "$LOG" 2>&1 &
PY=$!
echo "launched python pid=$PY (floor=${FLOOR_MB}MB)"
while kill -0 $PY 2>/dev/null; do
  free=$(df -m /System/Volumes/Data | awk 'NR==2{print $4}')
  done=$(grep -c 'crash_real=' "$LOG" 2>/dev/null || echo 0)
  rawmb=$(du -m "$RAW" 2>/dev/null | cut -f1)
  echo "$(date '+%T') guard: free=${free}MB done=${done}/19 raw=${rawmb}MB"
  if [ "${free:-0}" -lt "$FLOOR_MB" ]; then
    echo "!! DISK GUARD TRIP: free ${free}MB < ${FLOOR_MB}MB — killing run to avoid corruption"
    kill $PY 2>/dev/null; sleep 3
    docker rm -f $(docker ps -aq --filter name=t1c_ 2>/dev/null) 2>/dev/null
    break
  fi
  sleep 20
done
wait $PY 2>/dev/null; rc=$?
echo "GUARDED T1 ENDED rc=$rc free=$(df -m /System/Volumes/Data | awk 'NR==2{print $4}')MB done=$(grep -c 'crash_real=' "$LOG" 2>/dev/null||echo 0)/19"
