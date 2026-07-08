#!/usr/bin/env python3
"""cov_collect — REPO-AWARE failing-test execution coverage (the DYNAMIC half's input).

The old pytest-only collector (hybrid_loop_v2.run_coverage) returns 0 lines for Django, which uses
its OWN runner (`tests/runtests.py`) not pytest, and whose FAIL_TO_PASS names are unittest-style
(`test_method (module.Class)` or a docstring) that pytest can't take. This collector instead derives
the test target from the TEST_PATCH (the files it modifies hold the FAIL_TO_PASS tests) and runs them
with the RIGHT runner per repo, under `coverage`, in the official SWE-bench Docker image.

  collect(iid, row) -> {repo_relative_source_file: set(executed_line_numbers)}   ({} on any failure)

Coverage is a LOCALIZATION SIGNAL, so running the failing test's whole MODULE/FILE (not only the one
method) is fine — it still executes the buggy region; over-inclusion only softens, never breaks, the
delta*covered boost. Reuses egl_makeorbreak (docker/img_tag) + p7 (norm/is_repo_src). Image rm+rmi
per instance (disk-safe); parallelize at the caller.
"""
from __future__ import annotations
import json, os, re, sys, tempfile
import p0_line_recall as p0
import egl_makeorbreak as egl
import p7_crossfile_exec as p7

MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple"


def _is_testfile(f):
    """An actual test MODULE (contains tests) — not a fixture/sample under tests/roots/ etc.
    Django's convention is a bare `tests.py` (or app `tests/` package), so recognize it too — otherwise
    _test_files falls back to ALL touched .py (incl. fixture models.py/fields.py), which become bogus
    runtests labels."""
    b = f.replace("\\", "/").rsplit("/", 1)[-1]
    is_test = b.startswith("test_") or b.endswith("_test.py") or b == "tests.py"
    return is_test and "/roots/" not in f and "/data/" not in f


def _test_files(row):
    """Actual test files touched by the test_patch (drop fixture/sample modules like tests/roots/*.py,
    which pytest can't collect as tests -> would yield 0 coverage, e.g. sphinx). Falls back to all .py
    if the patch has no obvious test_*.py (rare)."""
    files = [f for f in p0.parse_patch(row.get("test_patch") or "") if f.endswith(".py")]
    tests = [f for f in files if _is_testfile(f)]
    return tests or files


def _django_label(f):
    """tests/test_utils/tests.py -> test_utils.tests  (Django runtests.py test label)."""
    f = f.replace("\\", "/")
    if f.startswith("tests/"):
        f = f[len("tests/"):]
    if f.endswith(".py"):
        f = f[:-3]
    return f.replace("/", ".")


def _test_cmd(repo, test_files):
    """Repo-aware coverage-wrapped command to run the failing test file(s)."""
    if repo == "django/django":
        labels = " ".join(_django_label(f) for f in test_files)
        # PYTHONPATH=/testbed/tests: newer Django runtests.py relies on sys.path[0] to import the
        # test_sqlite settings, but `python -m coverage run ./tests/runtests.py` doesn't set it the way
        # `python ./tests/runtests.py` does -> ModuleNotFoundError: test_sqlite -> runtests aborts in
        # setup and ONLY boot/import coverage is captured (196 identical files, test body never runs).
        # Older Django self-inserted tests/ so it worked; this makes it universal (redundant for old).
        # `env PYTHONPATH=...` (not a bare VAR=val prefix): the command is wrapped in `timeout 1500 %CMD%`,
        # and timeout execs its argument directly, so an inline assignment would be treated as the command.
        return ("env PYTHONPATH=/testbed/tests python -m coverage run --source=/testbed ./tests/runtests.py "
                f"--settings=test_sqlite --parallel 1 {labels}")
    tf = " ".join(f"'{f}'" for f in test_files)                 # pytest-native repos
    return ('python -m coverage run --source=/testbed -m pytest -p no:cacheprovider '
            f'-o addopts="" --tb=no -q {tf}')


CONTAINER_SH = r'''
source /opt/miniconda3/etc/profile.d/conda.sh 2>/dev/null || true
conda activate testbed 2>/dev/null || true
cd /testbed
python -c "import coverage" 2>/dev/null || python -m pip -q install coverage 2>/dev/null || python -m pip -q install -i %MIRROR% coverage 2>/dev/null || true
python -c "import pytest" 2>/dev/null || python -m pip -q install pytest 2>/dev/null || python -m pip -q install -i %MIRROR% pytest 2>/dev/null || true
( git apply /tmp/test.patch 2>/dev/null && echo APPLY_OK ) || ( git apply --3way /tmp/test.patch 2>/dev/null && echo APPLY_OK ) || echo APPLY_FAILED
python -m coverage erase 2>/dev/null || true
timeout 1500 %TEST_CMD% > /tmp/test.out 2>&1 || true
python -m coverage json -o /tmp/cov.json 2>/dev/null && echo COVJSON_OK || echo COVJSON_FAILED
echo ---TESTOUT_TAIL---
tail -c 1200 /tmp/test.out
'''


def collect(iid, row, pull_timeout=1800, keep_image=False, debug=False):
    """{repo_relative_source_file: set(executed lines)} from the failing test under coverage."""
    repo = row["repo"]; tag = egl.img_tag(iid)
    cont = "covc_" + re.sub(r"[^a-z0-9_]", "_", iid.lower())
    test_files = _test_files(row)
    exec_lines = {}
    if not test_files:
        if debug: print("  no test files in test_patch", file=sys.stderr)
        return exec_lines
    sh = CONTAINER_SH.replace("%MIRROR%", MIRROR).replace("%TEST_CMD%", _test_cmd(repo, test_files))
    try:
        if egl.docker("image", "inspect", tag).returncode != 0:
            if egl.docker("pull", tag, timeout=pull_timeout).returncode != 0:
                if debug: print("  pull failed", file=sys.stderr)
                return exec_lines
        egl.docker("rm", "-f", cont)
        egl.docker("run", "-d", "--name", cont, tag, "sleep", "infinity")
        try:
            ptxt = (row.get("test_patch") or "").replace("\r\n", "\n")
            if not ptxt.endswith("\n"): ptxt += "\n"
            tp = os.path.join(tempfile.gettempdir(), f"covc_{iid.replace('/', '_')}.patch")
            open(tp, "wb").write(ptxt.encode()); egl.docker("cp", tp, f"{cont}:/tmp/test.patch"); os.unlink(tp)
            ex = egl.docker("exec", cont, "bash", "-lc", sh, timeout=1800)
            if debug:
                print("  exec rc=%s\n%s" % (ex.returncode, ex.stdout[-1200:]), file=sys.stderr)
            cj = egl.docker("exec", cont, "cat", "/tmp/cov.json")
            if cj.returncode == 0 and cj.stdout.strip():
                cov = json.loads(cj.stdout)
                for fp, fd in cov.get("files", {}).items():
                    nf = p7.norm(fp); el = fd.get("executed_lines")
                    if el and p7.is_repo_src(nf):
                        exec_lines[nf] = set(el)
        finally:
            egl.docker("rm", "-f", cont)
            if not keep_image: egl.docker("rmi", tag)
    except Exception as e:
        if debug: print("  EXC", repr(e)[:120], file=sys.stderr)
    return exec_lines


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--iid", required=True)
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()
    rows = {r["instance_id"]: r for r in p0.load_rows(500)}
    row = rows[args.iid]
    el = collect(args.iid, row, debug=args.debug)
    nlines = sum(len(v) for v in el.values())
    print(f"{args.iid}  repo={row['repo']}  files_with_cov={len(el)}  exec_lines={nlines}")
    gf = p0.parse_patch(row.get("patch") or "")
    for f in [x for x in gf if x.endswith(".py")]:
        gold = gf[f]["region"]; cov = el.get(f, set())
        hit = len(gold & cov) if gold else 0
        print(f"  GOLD {f}: {len(gold)} gold lines, coverage hits {hit}/{len(gold)}"
              + ("  <-- coverage covers the bug" if hit else "  <-- coverage MISSED gold"))
