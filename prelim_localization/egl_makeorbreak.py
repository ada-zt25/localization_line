#!/usr/bin/env python3
"""EGL make-or-break: does DYNAMIC coverage of the gold reproduction test
localize the decisive (gold) lines, and does it beat the frontier LLM's STATIC
line localization?

For each instance: pull the SWE-bench prebuilt image (repo at base_commit + env),
apply the gold test_patch (adds FAIL_TO_PASS tests), run those FAILING tests under
coverage.py, and collect which lines of the gold-edited file were executed.

Metrics:
  H1 cov_recall  = |covered ∩ gold| / |gold|   -- does the failing test even
                   execute the decisive lines? (necessary condition for EGL)
  cov_lines      = how many lines the test covers in the gold file (the raw
                   coverage candidate-set size; precision context)
Compared against the frontier LLM static prediction (loaded from p0/p1 results
if available, else just reports coverage stats).

    docker must be on PATH. Usage:
    MODEL... python egl_makeorbreak.py --instances astropy__astropy-12907 ...
    or --sample 12 (auto-pick across pytest repos)
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, tempfile, time
from pathlib import Path
import p0_line_recall as p0

HERE = Path(__file__).resolve().parent
DOCKER = os.environ.get("DOCKER_BIN", "docker")

def img_tag(iid):
    return f"swebench/sweb.eval.x86_64.{iid.replace('__','_1776_')}:latest"

def sh(args, timeout=1800, check=False):
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if check and r.returncode != 0:
        raise RuntimeError(f"cmd failed ({r.returncode}): {' '.join(args[:3])}\n{r.stderr[-800:]}")
    return r

def docker(*args, **kw):
    return sh([DOCKER, *args], **kw)

# in-container script: activate env, apply test patch, run FAIL_TO_PASS under coverage, dump json
MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple"
CONTAINER_SH = r'''
source /opt/miniconda3/etc/profile.d/conda.sh 2>/dev/null || true
conda activate testbed 2>/dev/null || true
cd /testbed
python -c "import coverage" 2>/dev/null || python -m pip -q install coverage 2>/dev/null || python -m pip -q install -i %MIRROR% coverage 2>/dev/null || true
python -c "import pytest" 2>/dev/null || python -m pip -q install pytest 2>/dev/null || python -m pip -q install -i %MIRROR% pytest 2>/dev/null || true
( git apply -v /tmp/test.patch 2>/tmp/applyerr && echo APPLY_OK ) || ( git apply --3way /tmp/test.patch 2>>/tmp/applyerr && echo APPLY_OK ) || echo APPLY_FAILED
python -m coverage erase 2>/dev/null || true
python -m coverage run --source=/testbed -m pytest -p no:cacheprovider -q --no-header -o addopts="" %TESTS% > /tmp/pytest.out 2>&1 || true
( python -m coverage json -o /tmp/cov.json 2>/tmp/coverr && echo COVJSON_OK ) || echo COVJSON_FAILED
echo "---PYTEST_TAIL---"
tail -8 /tmp/pytest.out
'''

def run_instance(iid, row, keep_image=False, pull_timeout=1800):
    res = {"instance_id": iid}
    files = p0.parse_patch(row.get("patch") or "")
    py = [f for f in files if f.endswith(".py")]
    if len(py) != 1:
        res["error"] = "not single .py"; return res
    gold_path = py[0]; gold = files[gold_path]["region"]
    res["gold_path"] = gold_path; res["n_gold"] = len(gold)
    ftp = row.get("FAIL_TO_PASS")
    if isinstance(ftp, str):
        try: ftp = json.loads(ftp)
        except: ftp = []
    if not ftp:
        res["error"] = "no FAIL_TO_PASS"; return res
    tag = img_tag(iid); cont = "egl_" + iid.replace("__", "_").replace("-", "_")
    # pull if missing
    if docker("image", "inspect", tag).returncode != 0:
        t0 = time.time()
        p = docker("pull", tag, timeout=pull_timeout)
        res["pull_s"] = round(time.time() - t0, 1)
        if p.returncode != 0:
            res["error"] = "pull failed: " + p.stderr[-300:]; return res
    docker("rm", "-f", cont)
    r = docker("run", "-d", "--name", cont, tag, "sleep", "infinity")
    if r.returncode != 0:
        res["error"] = "run failed: " + r.stderr[-300:]; return res
    try:
        # copy test patch -- write with LF only (Windows text mode would emit CRLF
        # and git apply rejects CRLF patches), ensure trailing newline.
        patch_txt = (row.get("test_patch") or "").replace("\r\n", "\n").replace("\r", "\n")
        if not patch_txt.endswith("\n"):
            patch_txt += "\n"
        tp = os.path.join(tempfile.gettempdir(), f"egl_{iid.replace('/','_')}.patch")
        with open(tp, "wb") as tf:
            tf.write(patch_txt.encode("utf-8"))
        docker("cp", tp, f"{cont}:/tmp/test.patch")
        os.unlink(tp)
        tests = " ".join(f"'{t}'" for t in ftp[:10])
        script = CONTAINER_SH.replace("%TESTS%", tests).replace("%MIRROR%", MIRROR)
        ex = docker("exec", cont, "bash", "-lc", script, timeout=1800)
        res["pytest_tail"] = ex.stdout.split("---PYTEST_TAIL---")[-1].strip()[-400:] if "---PYTEST_TAIL---" in ex.stdout else ex.stdout[-300:]
        res["apply_ok"] = "APPLY_OK" in ex.stdout
        res["covjson_ok"] = "COVJSON_OK" in ex.stdout
        # pull coverage json
        cj = docker("exec", cont, "cat", "/tmp/cov.json")
        if cj.returncode != 0 or not cj.stdout.strip():
            res["error"] = "no coverage json; stderr=" + (ex.stderr[-300:])
            return res
        cov = json.loads(cj.stdout)
        # find gold file in coverage (match by path suffix)
        covered = set()
        matched = None
        for fpath, fdata in cov.get("files", {}).items():
            if fpath.replace("\\", "/").endswith(gold_path):
                covered = set(fdata.get("executed_lines", [])); matched = fpath; break
        res["cov_file_matched"] = matched
        res["cov_lines_in_goldfile"] = len(covered)
        inter = covered & gold
        res["cov_recall"] = round(len(inter) / len(gold), 3) if gold else 0.0
        res["covered_gold"] = sorted(inter)
        res["gold_lines"] = sorted(gold)
        # cleaner: coverage recall vs DELETED gold lines (executable buggy lines)
        gold_del = files[gold_path].get("deleted", set())
        res["n_gold_del"] = len(gold_del)
        res["cov_recall_del"] = round(len(covered & gold_del) / len(gold_del), 3) if gold_del else None
        # ---- head-to-head: frontier LLM static localization on the exact file ----
        try:
            fr = docker("exec", cont, "cat", f"/testbed/{gold_path}")
            if fr.returncode == 0 and fr.stdout:
                srclines = fr.stdout.splitlines()
                # function-expanded coverage candidate: lines of any function the
                # failing test ENTERED (higher recall than exact executed lines --
                # rescues insertions / untaken branches inside an executed function).
                l2f = p0.line_to_func(fr.stdout)
                exec_funcs = {l2f[ln] for ln in covered if ln in l2f}
                func_cand = {ln for ln, nm in l2f.items() if nm in exec_funcs}
                res["funccov_cand_lines"] = len(func_cand)
                res["funccov_recall"] = round(len(func_cand & gold) / len(gold), 3) if gold else 0.0
                res["funccov_recall_del"] = round(len(func_cand & gold_del) / len(gold_del), 3) if gold_del else None
                numbered = "\n".join(f"{i+1}: {ln}" for i, ln in enumerate(srclines))
                issue = (row.get("problem_statement") or "")[:6000]
                out = p0.call_model("openai", os.environ.get("MODEL", "deepseek-ai/DeepSeek-V3"),
                                    p0.PROMPT.format(issue=issue, path=gold_path, numbered=numbered))
                pred, _ = p0.parse_ranges(out)
                res["file_lines"] = len(srclines)
                res["llm_pred_lines"] = len(pred)
                res["llm_recall"] = round(len(pred & gold) / len(gold), 3) if gold else 0.0
                res["llm_precision"] = round(len(pred & gold) / len(pred), 3) if pred else 0.0
                fused = pred & covered  # restrict LLM picks to executed lines
                res["fused_pred_lines"] = len(fused)
                res["fused_recall"] = round(len(fused & gold) / len(gold), 3) if gold else 0.0
                res["fused_precision"] = round(len(fused & gold) / len(fused), 3) if fused else 0.0
        except Exception as e:
            res["llm_error"] = repr(e)[:200]
        res["cov_total_lines_allfiles"] = sum(len(f.get("executed_lines", [])) for f in cov.get("files", {}).values())
        res["cov_nfiles"] = len(cov.get("files", {}))
    finally:
        docker("rm", "-f", cont)
        if not keep_image:
            docker("rmi", tag)
    return res

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instances", nargs="*", default=[])
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--keep-image", action="store_true")
    ap.add_argument("--out", default=str(HERE / "egl_coverage_results.json"))
    args = ap.parse_args()

    rows = {r["instance_id"]: r for r in p0.load_rows(500)}
    ids = list(args.instances)
    if args.sample:
        # pytest-NATIVE repos (env ships pytest, FAIL_TO_PASS are node ids). sympy
        # excluded: its env lacks pytest and uses bare function-name test ids (needs
        # its own runner -> deferred to harness-hardening).
        PYTEST_REPOS = {"astropy/astropy","scikit-learn/scikit-learn",
                        "pydata/xarray","psf/requests","matplotlib/matplotlib","pallets/flask"}
        import random as _rnd
        pool = [iid for iid, r in rows.items() if r["repo"] in PYTEST_REPOS]
        # single-file with FAIL_TO_PASS
        good = []
        for iid in pool:
            r = rows[iid]; files = p0.parse_patch(r.get("patch") or "")
            if len([f for f in files if f.endswith(".py")]) == 1 and len(files) == 1:
                good.append(iid)
        _rnd.Random(1).shuffle(good)
        ids = good[:args.sample]

    results = []
    out = Path(args.out)
    existing = {}
    if out.exists():
        try: existing = {r["instance_id"]: r for r in json.loads(out.read_text())["results"]}
        except: pass
    for i, iid in enumerate(ids):
        if iid in existing and "cov_recall" in existing[iid]:
            results.append(existing[iid]); print(f"[{i+1}/{len(ids)}] {iid} CACHED cov_recall={existing[iid]['cov_recall']}", file=sys.stderr); continue
        print(f"[{i+1}/{len(ids)}] {iid} ...", file=sys.stderr)
        try:
            r = run_instance(iid, rows[iid], keep_image=args.keep_image)
        except Exception as e:
            r = {"instance_id": iid, "error": repr(e)[:300]}
        results.append(r)
        msg = (f"cov_recall={r.get('cov_recall')} cov_lines={r.get('cov_lines_in_goldfile')} "
               f"n_gold={r.get('n_gold')} err={r.get('error','')}")
        print(f"    -> {msg}", file=sys.stderr)
        out.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")  # checkpoint

    ok = [r for r in results if "cov_recall" in r]
    if ok:
        import statistics as st
        summary = {"n": len(ok),
                   "mean_cov_recall": round(st.mean(r["cov_recall"] for r in ok), 3),
                   "cov_recall>=0.99 frac": round(sum(1 for r in ok if r["cov_recall"] >= 0.99) / len(ok), 3),
                   "cov_recall==0 frac": round(sum(1 for r in ok if r["cov_recall"] == 0) / len(ok), 3),
                   "mean_cov_lines_goldfile": round(st.mean(r["cov_lines_in_goldfile"] for r in ok), 1),
                   "mean_n_gold": round(st.mean(r["n_gold"] for r in ok), 1)}
        print("\n==== SUMMARY ====\n" + json.dumps(summary, indent=2), file=sys.stderr)
        d = json.loads(out.read_text()); d["summary"] = summary; out.write_text(json.dumps(d, indent=2), encoding="utf-8")
    print(f"written: {out}", file=sys.stderr)

if __name__ == "__main__":
    main()
