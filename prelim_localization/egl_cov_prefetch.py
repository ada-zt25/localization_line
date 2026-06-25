#!/usr/bin/env python3
"""egl_cov_prefetch — populate egl_cov_cache.json (per-file EXECUTED lines from the official
SWE-bench Docker images) for the head-to-head SieveFL arm, INDEPENDENTLY of the LLM vote phase
so the two can run in parallel. Writes ONLY egl_cov_cache.json (never egl_headtohead.json).

    python egl_cov_prefetch.py --sample 13
"""
from __future__ import annotations
import argparse, sys
import egl_headtohead as h2h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=13)
    args = ap.parse_args()
    rows, pool = h2h.select_pool(args.sample)
    for idx, iid in enumerate(pool):
        cov = h2h.load_cov(iid, rows[iid], want_exec=True)
        nfiles = len(cov); nlines = sum(len(v) for v in cov.values())
        print(f"[cov {idx+1}/{len(pool)}] {iid:30s} files_with_cov={nfiles} exec_lines={nlines}",
              file=sys.stderr); sys.stderr.flush()


if __name__ == "__main__":
    main()
