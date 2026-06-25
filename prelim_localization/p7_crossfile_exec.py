#!/usr/bin/env python3
"""P7: SCOPED make-or-break for the user's refined idea -- on MULTI-FILE issues,
can EXECUTION EVIDENCE (failing-test coverage + traceback file naming) recover the
gold files that STATIC LLM file-localization MISSED?

This targets P2's bottleneck (multi-file: file_recall@10=0.66, all-files-found=0.35).
Combines both signals the user proposed: traceback (error feedback) + coverage.

Per multi-file instance:
  static_files   = LLM picks top-k files from the repo .py list
  tb_files       = repo .py files named in the failing-test traceback
  cov_files      = repo .py files with >=1 executed line (coverage)
Compare file-level recall of gold files: static vs static+tb vs static+tb+cov,
and how many static-missed gold files execution recovers.

    OPENAI_BASE_URL=https://api.siliconflow.com/v1 MODEL=deepseek-ai/DeepSeek-V3 \
        python p7_crossfile_exec.py
"""
from __future__ import annotations
import argparse, json, os, re, sys, tempfile
from pathlib import Path
import p0_line_recall as p0
import p1_realistic as p1
import egl_makeorbreak as egl

HERE = Path(__file__).resolve().parent
MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple"
PYTEST = {"astropy/astropy","scikit-learn/scikit-learn","pydata/xarray",
          "psf/requests","matplotlib/matplotlib","pallets/flask"}

RUN_SH = r'''
source /opt/miniconda3/etc/profile.d/conda.sh 2>/dev/null || true
conda activate testbed 2>/dev/null || true
cd /testbed
python -c "import coverage" 2>/dev/null || python -m pip -q install coverage 2>/dev/null || python -m pip -q install -i %MIRROR% coverage 2>/dev/null || true
python -c "import pytest" 2>/dev/null || python -m pip -q install pytest 2>/dev/null || python -m pip -q install -i %MIRROR% pytest 2>/dev/null || true
( git apply /tmp/test.patch 2>/dev/null && echo APPLY_OK ) || ( git apply --3way /tmp/test.patch 2>/dev/null && echo APPLY_OK ) || echo APPLY_FAILED
python -m coverage erase 2>/dev/null || true
python -m coverage run --source=/testbed -m pytest -p no:cacheprovider --no-header -o addopts="" --tb=short -q %TESTS% > /tmp/pytest.out 2>&1 || true
python -m coverage json -o /tmp/cov.json 2>/dev/null && echo COVJSON_OK || echo COVJSON_FAILED
python /tmp/narrow.py > /tmp/called.json 2>/dev/null && echo CALLED_OK || echo CALLED_FAILED
echo ---FAILOUT---
tail -c 4500 /tmp/pytest.out
'''

# In-container: narrow coverage to files whose FUNCTION BODIES executed (i.e.
# functions actually CALLED), excluding files only touched at import time
# (module-level / def-header lines). This is the user's refinement.
NARROW_PY = r'''import json,ast,os
try: cov=json.load(open("/tmp/cov.json"))
except Exception: cov={"files":{}}
called=[]
for path,d in cov.get("files",{}).items():
    ex=set(d.get("executed_lines") or [])
    if not ex: continue
    fp=path if os.path.exists(path) else os.path.join("/testbed",path)
    try: tree=ast.parse(open(fp,encoding="utf-8",errors="replace").read())
    except Exception: continue
    body=set()
    for n in ast.walk(tree):
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.body:
            s=n.body[0].lineno; e=getattr(n,"end_lineno",s) or s
            body.update(range(s,e+1))
    if ex & body: called.append(path)
print(json.dumps(called))
'''

def is_repo_src(path):
    p = path.replace("\\", "/")
    bad = ("site-packages", "miniconda", "/.tox/", "/tests/", "conftest", "/test/")
    if any(b in p for b in bad): return False
    base = p.rsplit("/", 1)[-1]
    if base.startswith("test_") or base.endswith("_test.py"): return False
    return p.endswith(".py")

def norm(path):  # strip leading /testbed/ and ./
    p = path.replace("\\", "/")
    if p.startswith("/testbed/"): p = p[len("/testbed/"):]
    if p.startswith("./"): p = p[2:]
    return p

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topk", type=int, default=10)
    ap.add_argument("--out", default=str(HERE / "p7_crossfile_exec.json"))
    args = ap.parse_args()
    model = os.environ.get("MODEL", "deepseek-ai/DeepSeek-V3")

    rows = {r["instance_id"]: r for r in p0.load_rows(500)}
    cands = []
    for iid, r in rows.items():
        if r["repo"] not in PYTEST: continue
        files = p0.parse_patch(r.get("patch") or "")
        py = [f for f in files if f.endswith(".py") and files[f]["hunks"]]
        if len(py) >= 2 and len(py) == len([f for f in files if f.endswith(".py")]) and r.get("FAIL_TO_PASS"):
            cands.append(iid)
    print(f"[P7] selected {len(cands)} multi-file pytest-native instances", file=sys.stderr); sys.stderr.flush()

    out = Path(args.out)
    results = json.loads(out.read_text())["results"] if out.exists() else []
    out.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")  # ensure file exists
    done = {r["instance_id"] for r in results if r.get("fr_static") is not None}

    for i, iid in enumerate(cands):
        if iid in done:
            print(f"[{i+1}/{len(cands)}] {iid} cached", file=sys.stderr); continue
        r = rows[iid]; files = p0.parse_patch(r.get("patch") or "")
        gold_files = {f for f in files if f.endswith(".py")}
        ftp = r.get("FAIL_TO_PASS")
        if isinstance(ftp, str):
            try: ftp = json.loads(ftp)
            except: ftp = []
        rec = {"instance_id": iid, "repo": r["repo"], "gold_files": sorted(gold_files)}
        # ---- static file localization ----
        try:
            tree = p1.fetch_tree(r["repo"], r["base_commit"])
            fp = p1.FILE_PROMPT.format(issue=(r.get("problem_statement") or "")[:5000],
                                       nfiles=len(tree["paths"]), filelist="\n".join(tree["paths"]))
            static_files = set(p1.parse_str_list(p0.call_model("openai", model, fp))[:args.topk])
        except Exception as e:
            rec["error"] = "static/tree: " + repr(e)[:150]; results.append(rec)
            out.write_text(json.dumps({"results": results}, indent=2)); print(rec["error"], file=sys.stderr); continue
        # ---- execution: coverage + traceback ----
        tag = egl.img_tag(iid); cont = "p7_" + re.sub(r'[^a-z0-9_]', '_', iid.lower())
        cov_files = set(); tb_files = set(); called_files = set(); apply_ok = False
        try:
            if egl.docker("image", "inspect", tag).returncode != 0:
                if egl.docker("pull", tag, timeout=1800).returncode != 0:
                    rec["error"] = "pull failed"; results.append(rec); out.write_text(json.dumps({"results": results}, indent=2)); print("pull failed", file=sys.stderr); continue
            egl.docker("rm", "-f", cont)
            egl.docker("run", "-d", "--name", cont, tag, "sleep", "infinity")
            try:
                ptxt = (r.get("test_patch") or "").replace("\r\n", "\n")
                if not ptxt.endswith("\n"): ptxt += "\n"
                tp = os.path.join(tempfile.gettempdir(), f"p7_{iid.replace('/','_')}.patch")
                open(tp, "wb").write(ptxt.encode()); egl.docker("cp", tp, f"{cont}:/tmp/test.patch"); os.unlink(tp)
                npy = os.path.join(tempfile.gettempdir(), f"p7_narrow.py")
                open(npy, "wb").write(NARROW_PY.encode()); egl.docker("cp", npy, f"{cont}:/tmp/narrow.py")
                tests = " ".join(f"'{t}'" for t in ftp[:6])
                sh = RUN_SH.replace("%TESTS%", tests).replace("%MIRROR%", MIRROR)
                ex = egl.docker("exec", cont, "bash", "-lc", sh, timeout=1800)
                apply_ok = "APPLY_OK" in ex.stdout
                failout = ex.stdout.split("---FAILOUT---")[-1] if "---FAILOUT---" in ex.stdout else ex.stdout[-4000:]
                # traceback files: paths like  path/file.py:123:
                for m in re.findall(r"([A-Za-z0-9_./-]+\.py):\d+", failout):
                    nf = norm(m)
                    if is_repo_src(nf): tb_files.add(nf)
                # coverage files
                cj = egl.docker("exec", cont, "cat", "/tmp/cov.json")
                if cj.returncode == 0 and cj.stdout.strip():
                    cov = json.loads(cj.stdout)
                    for fpath, fdata in cov.get("files", {}).items():
                        if fdata.get("executed_lines"):
                            nf = norm(fpath)
                            if is_repo_src(nf): cov_files.add(nf)
                # called-files narrowing (user's refinement)
                cjf = egl.docker("exec", cont, "cat", "/tmp/called.json")
                if cjf.returncode == 0 and cjf.stdout.strip():
                    try:
                        for fpath in json.loads(cjf.stdout):
                            nf = norm(fpath)
                            if is_repo_src(nf): called_files.add(nf)
                    except Exception: pass
            finally:
                egl.docker("rm", "-f", cont); egl.docker("rmi", tag)
        except Exception as e:
            rec["error_exec"] = repr(e)[:150]
        # ---- metrics ----
        def fr(s): return round(len(s & gold_files) / len(gold_files), 3)
        rec.update({
            "apply_ok": apply_ok, "n_gold_files": len(gold_files),
            "n_static": len(static_files), "n_tb": len(tb_files),
            "n_cov": len(cov_files), "n_calledcov": len(called_files),
            "fr_static": fr(static_files),
            "fr_tb": fr(tb_files),
            "fr_cov": fr(cov_files),
            "fr_calledcov": fr(called_files),
            "fr_static_tb": fr(static_files | tb_files),
            "fr_static_tb_calledcov": fr(static_files | tb_files | called_files),
            "fr_static_tb_cov": fr(static_files | tb_files | cov_files),
            "recovered_by_tb": sorted((gold_files - static_files) & tb_files),
            "recovered_by_calledcov": sorted((gold_files - static_files) & called_files),
            "recovered_by_broadcov": sorted((gold_files - static_files) & cov_files),
            "missed_by_all": sorted(gold_files - (static_files | tb_files | cov_files)),
        })
        results.append(rec)
        out.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")
        print(f"[{i+1}/{len(cands)}] {iid:28s} gold={len(gold_files)} static={rec['fr_static']:.2f} "
              f"+tb={rec['fr_static_tb']:.2f} +tb+CALLEDcov={rec['fr_static_tb_calledcov']:.2f} "
              f"| calledcov={rec['n_calledcov']} vs broadcov={rec['n_cov']} files | "
              f"recov_calledcov={rec['recovered_by_calledcov']}", file=sys.stderr)
        sys.stderr.flush()

    ok = [r for r in results if r.get("fr_static") is not None]
    if ok:
        import statistics as st
        def mean(k): return round(st.mean(r[k] for r in ok), 3)
        summary = {"n": len(ok),
                   "fr_static": mean("fr_static"), "fr_tb_only": mean("fr_tb"),
                   "fr_calledcov_only": mean("fr_calledcov"), "fr_broadcov_only": mean("fr_cov"),
                   "fr_static+tb": mean("fr_static_tb"),
                   "fr_static+tb+CALLEDcov": mean("fr_static_tb_calledcov"),
                   "fr_static+tb+broadcov": mean("fr_static_tb_cov"),
                   "mean_n_tb_files": mean("n_tb"),
                   "mean_n_CALLEDcov_files": mean("n_calledcov"), "mean_n_broadcov_files": mean("n_cov"),
                   "all_gold_found_static": sum(1 for r in ok if r["fr_static"] >= 0.999),
                   "all_gold_found_static+tb": sum(1 for r in ok if r["fr_static_tb"] >= 0.999),
                   "all_gold_found_static+tb+CALLEDcov": sum(1 for r in ok if r["fr_static_tb_calledcov"] >= 0.999),
                   "all_gold_found_static+tb+broadcov": sum(1 for r in ok if r["fr_static_tb_cov"] >= 0.999),
                   "instances_calledcov_recovered_missed": sum(1 for r in ok if r["recovered_by_calledcov"])}
        d = json.loads(out.read_text()); d["summary"] = summary; out.write_text(json.dumps(d, indent=2), encoding="utf-8")
        print("\n==== SUMMARY ====\n" + json.dumps(summary, indent=2), file=sys.stderr)
    print(f"written: {out}", file=sys.stderr)

if __name__ == "__main__":
    main()
