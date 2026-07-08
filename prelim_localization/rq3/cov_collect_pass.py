#!/usr/bin/env python3
"""cov_collect_pass — PASSING-test (PASS_TO_PASS) execution coverage, for SBFL's differential signal.
Reuses cov_collect's Docker machinery but runs the PASS_TO_PASS test selectors (same module as the
failing test, but they pass) under coverage. SBFL suspicious = lines in FAILING-cov but NOT in this
PASSING-cov (the crash-specific path, with common import/infra noise subtracted).

pytest repos: run `pytest file::test ...` selectors (capped). django uses a different runner —
handled best-effort (skip → caller falls back to no-passing = pure coverage-filter).
  collect_passing(iid, row, cap=40) -> {repo_relative_source_file: set(executed lines)}  ({} on failure)
"""
from __future__ import annotations
import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _sys.path[:0]=[_d,_os.path.dirname(_d)]; _os.chdir(_os.path.dirname(_d))
import json, os, re, sys, tempfile
import p0_line_recall as p0
import egl_makeorbreak as egl
import p7_crossfile_exec as p7
from cov_collect import CONTAINER_SH, MIRROR

def _pass_selectors(row, cap=40, field="PASS_TO_PASS"):
    v = row.get(field)
    if isinstance(v, str):
        try: v = json.loads(v)
        except Exception: v = []
    sels = [s for s in (v or []) if "::" in s]                 # pytest file::test form only
    return sels[:cap]

def _pass_cmd(repo, selectors):
    if repo == "django/django" or not selectors:
        return None                                            # django/non-pytest: skip (best-effort)
    sl = " ".join(f"'{s}'" for s in selectors)
    return ('python -m coverage run --source=/testbed -m pytest -p no:cacheprovider '
            f'-o addopts="" --tb=no -q {sl}')

def collect_passing(iid, row, cap=40, keep_image=False, debug=False, field="PASS_TO_PASS"):
    repo = row["repo"]; tag = egl.img_tag(iid)
    cont = ("covp_" if field == "PASS_TO_PASS" else "covfi_") + re.sub(r"[^a-z0-9_]", "_", iid.lower())
    cmd = _pass_cmd(repo, _pass_selectors(row, cap, field))
    exec_lines = {}
    if not cmd:
        if debug: print("  no pytest PASS_TO_PASS (django/empty) -> skip", file=sys.stderr)
        return exec_lines
    sh = CONTAINER_SH.replace("%MIRROR%", MIRROR).replace("%TEST_CMD%", cmd)
    try:
        if egl.docker("image", "inspect", tag).returncode != 0:
            if egl.docker("pull", tag, timeout=1800).returncode != 0:
                if debug: print("  pull failed", file=sys.stderr)
                return exec_lines
        egl.docker("rm", "-f", cont)
        egl.docker("run", "-d", "--name", cont, tag, "sleep", "infinity")
        try:
            ptxt = (row.get("test_patch") or "").replace("\r\n", "\n")
            if not ptxt.endswith("\n"): ptxt += "\n"
            tp = os.path.join(tempfile.gettempdir(), f"covp_{iid.replace('/', '_')}.patch")
            open(tp, "wb").write(ptxt.encode()); egl.docker("cp", tp, f"{cont}:/tmp/test.patch"); os.unlink(tp)
            ex = egl.docker("exec", cont, "bash", "-lc", sh, timeout=1800)
            if debug: print("  exec rc=%s\n%s" % (ex.returncode, ex.stdout[-800:]), file=sys.stderr)
            cj = egl.docker("exec", cont, "cat", "/tmp/cov.json")
            if cj.returncode == 0 and cj.stdout.strip():
                cov = json.loads(cj.stdout)
                for fp, fd in cov.get("files", {}).items():
                    nf = p7.norm(fp); el = fd.get("executed_lines")
                    if el and p7.is_repo_src(nf): exec_lines[nf] = set(el)
        finally:
            egl.docker("rm", "-f", cont)
            if not keep_image: egl.docker("rmi", tag)
    except Exception as e:
        if debug: print("  EXC", repr(e)[:120], file=sys.stderr)
    return exec_lines

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--iid", required=True); ap.add_argument("--debug", action="store_true")
    a = ap.parse_args()
    rows = {r["instance_id"]: r for r in p0.load_rows(500, dataset="lite")}; row = rows[a.iid]
    el = collect_passing(a.iid, row, debug=a.debug)
    print(f"{a.iid} repo={row['repo']} PASSING files_with_cov={len(el)} exec_lines={sum(len(v) for v in el.values())}")
