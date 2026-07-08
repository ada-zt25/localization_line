#!/usr/bin/env python3
"""test_evidence — extract the FAILING TEST's evidence (expected-vs-observed) for the M5 assertion-grounded
reranker. This is the ONE signal ORTHOGONAL to execution coverage (memory: coverage / vote-counts / def-use
are all 'membership' signals that collapse to noise when used to RANK within the executed set; the test's
assertion is the only same-model, inference-time signal that distinguishes the buggy line from innocent
executed lines). Pulls: (1) FAIL_TO_PASS test name(s); (2) the added test body/assertions from test_patch;
(3) the observed traceback/error from the issue. No LLM, no network."""
import json, re

_TB = re.compile(r"Traceback \(most recent call last\)")
_KEY = re.compile(r"assert|raises|expect|==|!=|approx|isclose|pytest|with .*:")

def _as_list(v):
    if isinstance(v, str):
        try: return json.loads(v)
        except Exception: return [v]
    return v or []

def extract_test_evidence(row, max_chars=1600):
    """-> compact string: failing test name(s) + its assertions + the observed error. '' if nothing useful."""
    parts = []
    names = _as_list(row.get("FAIL_TO_PASS"))
    if names:
        parts.append("Failing test(s): " + ", ".join(str(n) for n in names[:3]))
    # added test code (the assertions = what the test CHECKS) from the test patch
    added = [ln[1:] for ln in (row.get("test_patch") or "").splitlines()
             if ln.startswith("+") and not ln.startswith("+++") and ln[1:].strip()]
    key = [l for l in added if _KEY.search(l)]
    show = (key or added)[:24]
    if show:
        parts.append("Test code / assertions (what it expects):\n" + "\n".join(l[:160] for l in show))
    # observed failure / traceback from the issue
    ps = row.get("problem_statement") or ""
    m = _TB.search(ps)
    if m:
        parts.append("Observed failure (from issue):\n" + ps[m.start():m.start() + 700])
    ev = "\n\n".join(parts)
    return ev[:max_chars]

if __name__ == "__main__":
    import sys, p0_line_recall as p0
    rows = {r["instance_id"]: r for r in p0.load_rows(500)}
    iid = sys.argv[1] if len(sys.argv) > 1 else next(iter(rows))
    print(f"=== evidence for {iid} ===\n" + extract_test_evidence(rows[iid]))
