import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _p=_os.path.dirname(_d); _sys.path[:0]=[_p]; _os.chdir(_p)
#!/usr/bin/env python3
"""collect_verified_cov — STAGE B for benchmark2: failing-test execution coverage for the Verified
crash-half candidates, via the official SWE-bench Docker images (identical collector to the 57's
egl_cov_cache: cov_collect.collect). Resumable; disk-safe (image rm+rmi per instance in cov_collect).

on-path is DECIDED at freeze time (freeze_benchmark2.py) from this coverage; this script only fills the
cache. Coverage {} (attempted, empty) is recorded so resume skips it; use --retry-empty to re-attempt.

  # after the strict-match audit passes:
  python newbench/collect_verified_cov.py --workers 4
  python newbench/collect_verified_cov.py --workers 4 --retry-empty     # re-run the empties
"""
import argparse, json, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import p0_line_recall as p0
import cov_collect

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
AUDIT = HERE / "audit_crash_half.json"
CACHE = HERE / "verified_cov_cache.json"


def load_cache():
    return json.loads(CACHE.read_text()) if CACHE.exists() else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4, help="concurrent Docker instances (disk: ~2GB each transient)")
    ap.add_argument("--retry-empty", action="store_true", help="re-attempt instances cached as empty {}")
    ap.add_argument("--force", action="store_true", help="re-collect the --only ids even if already cached (for fixed-collector re-runs)")
    ap.add_argument("--sample", type=int, default=0, help="first N candidates (0=all; for a smoke test)")
    ap.add_argument("--only", default="", help="comma-separated instance_ids to (re)collect (smoke)")
    ap.add_argument("--which", default="net_new", choices=["net_new", "all_strict"],
                    help="net_new = the 76 Verified-only benchmark2 pool; all_strict = all 99")
    args = ap.parse_args()

    audit = json.load(open(AUDIT))
    curated = HERE / "benchmark2_crash_half.json"
    if args.which == "net_new" and curated.exists():
        cand_ids = json.load(open(curated))["confirmed"]      # 75 = audit-curated (django-9296 excluded)
    else:
        key = "verified_net_new" if args.which == "net_new" else "verified_strict_crash_half"
        cand_ids = audit[key]
    if args.only:
        want = set(args.only.split(","))
        cand_ids = [i for i in cand_ids if i in want]
    if args.sample:
        cand_ids = cand_ids[:args.sample]

    rows = {r["instance_id"]: r for r in p0.load_rows(500, dataset="verified")}
    cache = load_cache()
    lock = threading.Lock()

    todo = []
    for iid in cand_ids:
        if iid in cache and not args.force and not (args.retry_empty and not cache[iid]):
            continue
        todo.append(iid)
    print(f"candidates={len(cand_ids)}  cached={len(cand_ids)-len(todo)}  to-collect={len(todo)}  "
          f"workers={args.workers}", file=sys.stderr)

    t0 = time.time(); done = [0]

    def work(iid):
        row = rows.get(iid)
        if not row:
            return iid, None, "no-row"
        try:
            cov = cov_collect.collect(iid, row)      # {file: set(lines)}
        except Exception as e:
            return iid, None, f"EXC {type(e).__name__}: {str(e)[:100]}"
        serial = {f: sorted(v) for f, v in cov.items()}
        # on-path preview against the audited gold_file/clean_gold
        rec = audit["records"].get(iid, {})
        gf = rec.get("gold_file"); gold = set(rec.get("clean_gold") or [])
        ex = cov_collect_cov_for(serial, gf)
        onpath = bool(gold & ex)
        with lock:
            cache[iid] = serial
            CACHE.write_text(json.dumps(cache))       # resumable checkpoint every instance
            done[0] += 1
        return iid, {"nfiles": len(serial), "nlines": sum(len(v) for v in serial.values()),
                     "gold_in_cov": len(gold & ex), "n_gold": len(gold), "onpath": onpath}, None

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = [ex.submit(work, iid) for iid in todo]
        for fut in as_completed(futs):
            iid, info, err = fut.result()
            if err:
                print(f"[--] {iid:34s} {err}", file=sys.stderr)
            else:
                tag = "ON-PATH" if info["onpath"] else "off/none"
                print(f"[{done[0]}/{len(todo)}] {iid:34s} files={info['nfiles']:3d} "
                      f"lines={info['nlines']:5d} gold∩cov={info['gold_in_cov']}/{info['n_gold']} "
                      f"{tag}  {int(time.time()-t0)}s", file=sys.stderr)
            sys.stderr.flush()

    # quick tally
    onp = 0; cov_ok = 0
    for iid in cand_ids:
        c = cache.get(iid) or {}
        if c: cov_ok += 1
        rec = audit["records"].get(iid, {})
        gold = set(rec.get("clean_gold") or []); ex = cov_collect_cov_for(c, rec.get("gold_file"))
        if gold & ex: onp += 1
    print(f"\n=== coverage tally ({args.which}) ===", file=sys.stderr)
    print(f"  candidates          : {len(cand_ids)}", file=sys.stderr)
    print(f"  coverage collected  : {cov_ok}", file=sys.stderr)
    print(f"  ON-PATH (gold∩cov)  : {onp}   <-- benchmark2 crash·on-path count (pending freeze)", file=sys.stderr)
    print(f"  cache: {CACHE}", file=sys.stderr)


def cov_collect_cov_for(cov_map, gf):
    """Same endswith matching cov_collect/freeze use to map a gold file to a coverage file."""
    if not gf or not cov_map:
        return set()
    if gf in cov_map:
        return set(cov_map[gf])
    for cf, cl in cov_map.items():
        if cf.endswith(gf) or gf.endswith(cf.split("/")[-1]):
            return set(cl)
    return set()


if __name__ == "__main__":
    main()
