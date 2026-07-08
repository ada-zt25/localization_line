#!/usr/bin/env python3
"""T1 / A3 — GPU re-label audit: validate the regex crash + on/off-path labels of the FROZEN crash
subset (S1 on-path + S3 off-path, 68 instances) against the REAL failing-test run in Docker.

Non-invasive: reuses cov_collect's container flow (egl image, test_patch apply, coverage) but ALSO
captures the failing-test output with --tb=short so we can see whether the test fails by raising an
exception (crash) vs a value assertion (behavioral), and recomputes gold∩coverage authoritatively.

Per-instance signals written to rq4/results/relabel_audit.json (resumable — skips done iids):
  subset(frozen) · is_crash_regex(=True by construction) · is_crash_real(heuristic) ·
  on_path_frozen(S1=True/S3=False) · on_path_real(gold∩fresh-cov) · has_traceback · exc_types ·
  test_reproduced · apply_ok · pulled · raw test-output tail (for human adjudication).

Acceptance (RQ4_SPEC / 修订清单 A3): crash/on-path flips ≤ single digits AND no change to S1 membership.
Run on the box where the swebench amd64 images are reachable.  Usage:
  python rq4/relabel_t1.py [--limit N] [--workers W] [--only IID] [--debug]
"""
from __future__ import annotations
import os as _os, sys as _sys
_d = _os.path.dirname(_os.path.abspath(__file__)); _sys.path[:0] = [_d, _os.path.dirname(_d)]
_os.chdir(_os.path.dirname(_d))                      # -> prelim_localization (so caches resolve)

import argparse, json, re, os, tempfile, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import p0_line_recall as p0
import egl_makeorbreak as egl
import p7_crossfile_exec as p7
import cov_collect as cc

FROZEN = os.path.join(_d, "frozen_subsets.json")
OUT    = os.path.join(_d, "results", "relabel_audit.json")
MARK   = "---TESTOUT_TAIL---"
EXC_RE = re.compile(r"\b([A-Z][A-Za-z0-9_]*(?:Error|Exception|Warning))\b")
TB_RE  = re.compile(r"Traceback \(most recent call last\)")

def _test_cmd_t1(repo, test_files):
    """Like cov_collect._test_cmd but --tb=short (keep tracebacks) so crashes are visible."""
    if repo == "django/django":
        labels = " ".join(cc._django_label(f) for f in test_files)
        return ("python -m coverage run --source=/testbed ./tests/runtests.py "
                f"--settings=test_sqlite --parallel 1 -v 2 {labels}")
    tf = " ".join(f"'{f}'" for f in test_files)
    return ('python -m coverage run --source=/testbed -m pytest -p no:cacheprovider '
            f'-o addopts="" --tb=short -q -rA {tf}')

CONTAINER_SH = r'''
export COLUMNS=240 LINES=80            # stop pytest -rA from truncating "ValueError" -> "ValueErr..."
source /opt/miniconda3/etc/profile.d/conda.sh 2>/dev/null || true
conda activate testbed 2>/dev/null || true
cd /testbed
python -c "import coverage" 2>/dev/null || python -m pip -q install coverage 2>/dev/null || python -m pip -q install -i %MIRROR% coverage 2>/dev/null || true
python -c "import pytest" 2>/dev/null || python -m pip -q install pytest 2>/dev/null || python -m pip -q install -i %MIRROR% pytest 2>/dev/null || true
( git apply /tmp/test.patch 2>/dev/null && echo APPLY_OK ) || ( git apply --3way /tmp/test.patch 2>/dev/null && echo APPLY_OK ) || echo APPLY_FAILED
python -m coverage erase 2>/dev/null || true
timeout 1500 %TEST_CMD% > /tmp/test.out 2>&1 || true
python -m coverage json -o /tmp/cov.json 2>/dev/null && echo COVJSON_OK || echo COVJSON_FAILED
echo ''' + MARK + r'''
tail -c 6000 /tmp/test.out
'''

def collect_full(iid, row, debug=False):
    """Returns dict: exec_lines{file:set}, test_out, apply_ok, pulled, rc, err."""
    repo = row["repo"]; tag = egl.img_tag(iid)
    cont = "t1c_" + re.sub(r"[^a-z0-9_]", "_", iid.lower())
    test_files = cc._test_files(row)
    res = {"exec_lines": {}, "test_out": "", "apply_ok": None, "pulled": None, "rc": None, "err": None}
    if not test_files:
        res["err"] = "no_test_files"; return res
    sh = CONTAINER_SH.replace("%MIRROR%", cc.MIRROR).replace("%TEST_CMD%", _test_cmd_t1(repo, test_files))
    try:
        if egl.docker("image", "inspect", tag).returncode != 0:
            if egl.docker("pull", tag, timeout=2400).returncode != 0:
                res["pulled"] = False; res["err"] = "pull_failed"; return res
            res["pulled"] = True
        else:
            res["pulled"] = "cached"
        egl.docker("rm", "-f", cont)
        egl.docker("run", "-d", "--name", cont, tag, "sleep", "infinity")
        try:
            ptxt = (row.get("test_patch") or "").replace("\r\n", "\n")
            if not ptxt.endswith("\n"): ptxt += "\n"
            tp = os.path.join(tempfile.gettempdir(), f"t1_{iid.replace('/', '_')}.patch")
            open(tp, "wb").write(ptxt.encode()); egl.docker("cp", tp, f"{cont}:/tmp/test.patch"); os.unlink(tp)
            ex = egl.docker("exec", cont, "bash", "-lc", sh, timeout=1800)
            res["rc"] = ex.returncode
            out = ex.stdout or ""
            res["apply_ok"] = "APPLY_OK" in out and "APPLY_FAILED" not in out.split(MARK)[0]
            res["test_out"] = out.split(MARK, 1)[1].strip() if MARK in out else out[-6000:]
            cj = egl.docker("exec", cont, "cat", "/tmp/cov.json")
            if cj.returncode == 0 and cj.stdout.strip():
                cov = json.loads(cj.stdout)
                for fp, fd in cov.get("files", {}).items():
                    nf = p7.norm(fp); el = fd.get("executed_lines")
                    if el and p7.is_repo_src(nf):
                        res["exec_lines"][nf] = set(el)
        finally:
            egl.docker("rm", "-f", cont)
            egl.docker("rmi", tag)                  # disk-safe: drop image after each instance
    except Exception as e:
        res["err"] = repr(e)[:160]
        if debug: print("  EXC", res["err"], file=_sys.stderr)
    return res

def audit_one(item, rows, debug=False):
    iid = item["instance_id"]; subset = item["_subset"]
    row = rows.get(iid)
    t0 = time.time()
    if not row:
        return {"instance_id": iid, "subset": subset, "err": "no_row"}
    r = collect_full(iid, row, debug=debug)
    gf = p0.parse_patch(row.get("patch") or "")
    gold_file = item.get("gold_file")
    gold = set(item.get("gold_lines") or (gf.get(gold_file, {}).get("region") or set()))
    cov_gold = r["exec_lines"].get(gold_file, set())
    on_path_real = bool(gold & cov_gold) if gold else None
    out = r["test_out"]
    exc = sorted(set(EXC_RE.findall(out)))
    has_tb = bool(TB_RE.search(out))
    err_exc = [e for e in exc if (e.endswith("Error") or e.endswith("Exception")) and e != "AssertionError"]
    low = out.lower()
    reproduced = bool(re.search(r"\b\d+\s+(failed|error)", low) or "failed (" in low
                      or "errors=" in low or "failures=" in low) and r.get("apply_ok") is not False
    # crash(real) = failing test raised a genuine (non-assertion) exception, not a value mismatch or warning
    is_crash_real = bool(reproduced and (has_tb or err_exc))
    is_assertion_fail = bool(reproduced and "AssertionError" in exc and not err_exc and not has_tb)
    return {
        "instance_id": iid, "subset": subset,
        "on_path_frozen": subset == "S1_crash_onpath",
        "on_path_real": on_path_real,
        "gold_hits": f"{len(gold & cov_gold)}/{len(gold)}",
        "is_crash_regex": True,                       # by construction (S1/S3 = crash subsets)
        "is_crash_real": is_crash_real,
        "fail_mode": ("crash" if is_crash_real else "assertion" if is_assertion_fail
                      else "reproduced_unclear" if reproduced else "not_reproduced"),
        "err_exc": err_exc, "has_traceback": has_tb, "exc_types": exc,
        "test_reproduced": bool(reproduced),
        "apply_ok": r.get("apply_ok"), "pulled": r.get("pulled"), "rc": r.get("rc"), "err": r.get("err"),
        "secs": round(time.time() - t0, 1),
        "test_out_tail": out[-3500:],
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--only", default="")
    ap.add_argument("--debug", action="store_true")
    a = ap.parse_args()

    rows = {r["instance_id"]: r for r in p0.load_rows(500, dataset="lite")}
    fz = json.load(open(FROZEN))
    cand = []
    for sub in ("S1_crash_onpath", "S3_crash_offpath"):
        for it in fz[sub]:
            it = dict(it); it["_subset"] = sub; cand.append(it)
    if a.only:
        cand = [c for c in cand if c["instance_id"] == a.only]

    done = {}
    if os.path.exists(OUT):
        try: done = {d["instance_id"]: d for d in json.load(open(OUT)).get("rows", [])
                     if not d.get("err")}            # errored/failed-pull rows retry on resume
        except Exception: done = {}
    todo = [c for c in cand if c["instance_id"] not in done]
    if a.limit: todo = todo[:a.limit]
    print(f"[T1] candidates={len(cand)} done={len(done)} todo={len(todo)} workers={a.workers}", file=_sys.stderr)

    results = list(done.values())
    def flush():
        rows_sorted = sorted(results, key=lambda d: (d.get("subset",""), d["instance_id"]))
        summ = summarize(rows_sorted)
        json.dump({"config": {"task": "T1_relabel_audit", "n": len(rows_sorted)},
                   "model": "docker-real-fail-test", "git_sha": os.environ.get("RQ4_GIT_SHA","uncommitted"),
                   "summary": summ, "rows": rows_sorted}, open(OUT, "w"), indent=1, ensure_ascii=False)

    if a.workers <= 1:
        for c in todo:
            d = audit_one(c, rows, a.debug); results.append(d)
            print(f"  {d['instance_id']:34} {d['subset'][:2]} crash_real={d.get('is_crash_real')} "
                  f"onpath_real={d.get('on_path_real')} hits={d.get('gold_hits')} tb={d.get('has_traceback')} "
                  f"{d.get('secs')}s err={d.get('err')}", file=_sys.stderr)
            flush()
    else:
        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            futs = {ex.submit(audit_one, c, rows, a.debug): c for c in todo}
            for f in as_completed(futs):
                d = f.result(); results.append(d)
                print(f"  {d['instance_id']:34} {d['subset'][:2]} crash_real={d.get('is_crash_real')} "
                      f"onpath_real={d.get('on_path_real')} hits={d.get('gold_hits')} {d.get('secs')}s "
                      f"err={d.get('err')}", file=_sys.stderr)
                flush()
    flush()
    print("[T1] summary:\n" + json.dumps(summarize(results), indent=1, ensure_ascii=False), file=_sys.stderr)

def summarize(rows):
    ok = [r for r in rows if not r.get("err")]
    s1 = [r for r in ok if r.get("subset") == "S1_crash_onpath"]
    s3 = [r for r in ok if r.get("subset") == "S3_crash_offpath"]
    crash_fp = [r["instance_id"] for r in ok if r.get("is_crash_real") is False]
    onpath_flip = [r["instance_id"] for r in ok if r.get("on_path_real") is not None
                   and r.get("on_path_real") != r.get("on_path_frozen")]
    return {
        "n_total": len(rows), "n_ok": len(ok), "n_err": len(rows) - len(ok),
        "n_S1": len(s1), "n_S3": len(s3),
        "crash_confirmed": sum(1 for r in ok if r.get("is_crash_real")),
        "crash_not_confirmed_ids": crash_fp,
        "onpath_flip_ids": onpath_flip,
        "S1_membership_changed": [i for i in crash_fp + onpath_flip
                                  if any(r["instance_id"] == i and r["subset"] == "S1_crash_onpath" for r in ok)],
    }

if __name__ == "__main__":
    main()
