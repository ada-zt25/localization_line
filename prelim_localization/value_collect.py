#!/usr/bin/env python3
"""value_collect — 付费版值追踪 (E2 输入). 在官方 SWE-bench Docker 里跑失败测试,
用 sys.settrace 行追踪器(作用域限定 /testbed 仓库文件)抓【每条执行仓库行的运行时值】.
复用 cov_collect 的 Docker 基建(egl/img_tag/_test_files/分runner). 与 coverage 正交, 不吞异常.

  collect(iid,row) -> {repo_relative_file: {line:int -> {var: value_repr}}}   ({} on failure)

注入方式: 往 /testbed 放 sitecustomize.py (解释器启动自动 import), tracer 在测试进程内生效.
tracer: 'call' 事件对非仓库/site-packages 帧返 None(跳过其行追踪, 省开销); 仓库帧每行留 f_locals
的标量/None/len 快照(数据级 bug 的判别信息), 每(文件,行)只留最后一次. atexit + SIGTERM 都 dump.
"""
from __future__ import annotations
import json, os, re, sys, tempfile
import p0_line_recall as p0
import egl_makeorbreak as egl
import p7_crossfile_exec as p7
import cov_collect as CC

MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple"

# --- 包装脚本: 同进程内先 settrace 再跑 test runner (保证 tracer 生效) ---
VWRAP = r'''
import sys, json, atexit, signal, os
CAP = {}          # "file:line" -> {var: repr}
LINECAP = 60000
def _sr(v):
    try:
        if v is None: return "None"
        t = type(v).__name__
        if isinstance(v, bool): return "bool=%s" % v
        if isinstance(v, (int, float)): return ("%s=%r" % (t, v))[:60]
        if isinstance(v, str): return ("str=%r" % v)[:60]
        if isinstance(v, (list, tuple, dict, set, frozenset)): return "%s(len=%d)" % (t, len(v))
        return t
    except Exception:
        return "?"
def _tr(fr, ev, arg):
    fn = fr.f_code.co_filename
    if ev == "call":
        return _tr if (fn.startswith("/testbed/") and "site-packages" not in fn) else None
    if len(CAP) < LINECAP:
        try:
            snap = {k: _sr(v) for k, v in fr.f_locals.items()
                    if not k.startswith("__") and len(k) <= 40}
            if snap:
                CAP["%s:%d" % (fn, fr.f_lineno)] = snap
        except Exception:
            pass
    return _tr
def _dump(*a):
    try: json.dump(CAP, open("/tmp/vtrace.json", "w"))
    except Exception: pass
atexit.register(_dump)
try: signal.signal(signal.SIGTERM, lambda *a: (_dump(), os._exit(0)))
except Exception: pass
mode = sys.argv[1]; rest = sys.argv[2:]
sys.settrace(_tr)
try:
    import threading; threading.settrace(_tr)
except Exception:
    pass
try:
    if mode == "pytest":
        import pytest; pytest.main(rest)
    elif mode == "django":
        import runpy
        sys.argv = ["./tests/runtests.py"] + rest
        try: runpy.run_path("tests/runtests.py", run_name="__main__")
        except SystemExit: pass
except SystemExit:
    pass
finally:
    _dump()
'''

def _wrap_cmd(repo, test_files):
    """用 /tmp/vwrap.py 同进程跑 test runner (tracer 内生效)."""
    if repo == "django/django":
        labels = " ".join(CC._django_label(f) for f in test_files)
        return ("env PYTHONPATH=/testbed/tests python /tmp/vwrap.py django "
                f"--settings=test_sqlite --parallel 1 {labels}")
    tf = " ".join(f"'{f}'" for f in test_files)
    return ("python /tmp/vwrap.py pytest -p no:cacheprovider -o addopts= --tb=no -q " + tf)

CONTAINER_SH = r'''
source /opt/miniconda3/etc/profile.d/conda.sh 2>/dev/null || true
conda activate testbed 2>/dev/null || true
cd /testbed
python -c "import pytest" 2>/dev/null || python -m pip -q install pytest 2>/dev/null || python -m pip -q install -i %MIRROR% pytest 2>/dev/null || true
( git apply /tmp/test.patch 2>/dev/null && echo APPLY_OK ) || ( git apply --3way /tmp/test.patch 2>/dev/null && echo APPLY_OK ) || echo APPLY_FAILED
rm -f /tmp/vtrace.json
timeout 1400 %TEST_CMD% > /tmp/test.out 2>&1 || true
test -f /tmp/vtrace.json && echo VTRACE_OK || echo VTRACE_FAILED
echo ---VTRACE_HEAD---; head -c 260 /tmp/vtrace.json; echo
echo ---TESTOUT_TAIL---
tail -c 500 /tmp/test.out
'''

def collect(iid, row, pull_timeout=1800, keep_image=False, debug=False):
    repo = row["repo"]; tag = egl.img_tag(iid)
    cont = "valc_" + re.sub(r"[^a-z0-9_]", "_", iid.lower())
    test_files = CC._test_files(row)
    out = {}
    if not test_files:
        if debug: print("  no test files", file=sys.stderr)
        return out
    sh = CONTAINER_SH.replace("%MIRROR%", MIRROR).replace("%TEST_CMD%", _wrap_cmd(repo, test_files))
    try:
        if egl.docker("image", "inspect", tag).returncode != 0:
            if egl.docker("pull", tag, timeout=pull_timeout).returncode != 0:
                if debug: print("  pull failed", file=sys.stderr)
                return out
        egl.docker("rm", "-f", cont)
        egl.docker("run", "-d", "--name", cont, tag, "sleep", "infinity")
        try:
            ptxt = (row.get("test_patch") or "").replace("\r\n", "\n")
            if not ptxt.endswith("\n"): ptxt += "\n"
            for name, content in [("test.patch", ptxt), ("vwrap.py", VWRAP)]:
                tp = os.path.join(tempfile.gettempdir(), f"valc_{iid.replace('/', '_')}_{name}")
                open(tp, "wb").write(content.encode()); egl.docker("cp", tp, f"{cont}:/tmp/{name}"); os.unlink(tp)
            ex = egl.docker("exec", cont, "bash", "-lc", sh, timeout=1700)
            if debug:
                print("  exec rc=%s\n%s" % (ex.returncode, ex.stdout[-900:]), file=sys.stderr)
            vj = egl.docker("exec", cont, "cat", "/tmp/vtrace.json")
            if vj.returncode == 0 and vj.stdout.strip():
                raw = json.loads(vj.stdout)
                for k, snap in raw.items():
                    fp, ln = k.rsplit(":", 1)
                    nf = p7.norm(fp)
                    if p7.is_repo_src(nf):
                        out.setdefault(nf, {})[int(ln)] = snap
        finally:
            egl.docker("rm", "-f", cont)
            if not keep_image: egl.docker("rmi", tag)
    except Exception as e:
        if debug: print("  EXC", repr(e)[:120], file=sys.stderr)
    return out

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--iid", required=True); ap.add_argument("--debug", action="store_true")
    a = ap.parse_args()
    rows = {r["instance_id"]: r for r in p0.load_rows(500)}
    row = rows[a.iid]
    vt = collect(a.iid, row, debug=a.debug)
    nlines = sum(len(v) for v in vt.values())
    print(f"{a.iid}  repo={row['repo']}  files={len(vt)}  traced_lines={nlines}")
    gf = p0.parse_patch(row.get("patch") or "")
    for f in [x for x in gf if x.endswith(".py")]:
        gold = gf[f]["region"]; vv = vt.get(f, {})
        hit = [ln for ln in gold if ln in vv] if gold else []
        print(f"  GOLD {f}: {len(gold)} gold lines, values-captured {len(hit)}")
        for ln in hit[:4]:
            print(f"    L{ln}: {vv[ln]}")
