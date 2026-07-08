import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _p=_os.path.dirname(_d); _sys.path[:0]=[_p]; _os.chdir(_p)
#!/usr/bin/env python3
"""curate_crash_half — apply the adversarial-audit verdict to the 76 net-new candidates and emit the
CANONICAL benchmark2 crash-half list. User decision (2026-07-06): exclude ONLY the single unanimously-
confirmed regex false-positive (django-9296), keep everything else; the frozen 57 are left untouched.

Emits newbench/benchmark2_crash_half.json = {confirmed:[75 ids], excluded:[{id,reason}], provenance}.
collect_verified_cov.py and freeze_benchmark2.py read `confirmed` from here."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIT = HERE / "audit_crash_half.json"
OUT = HERE / "benchmark2_crash_half.json"

# NOTE (coverage collection bugs found & fixed 2026-07-06, do not confuse with crash-half curation):
#  (1) newer Django: `coverage run ./tests/runtests.py` failed to import test_sqlite settings ->
#      test never ran -> boot-only coverage (196 identical files) -> ~20 instances FALSELY off-path.
#      Fixed in cov_collect._test_cmd via `env PYTHONPATH=/testbed/tests`. Re-collect Django <250 files.
#  (2) pytest repos occasionally returned files=0 under 4-worker Docker contention (not a command bug;
#      flask-5014 re-ran serially = ON-PATH). Re-collect the empty-coverage ones at low concurrency.
# on-path labels are only valid AFTER re-collection; see benchmark2 memory + doc.

# adversarial-audit verdict (wf_e08f116c-efa): unanimous EXCLUDE (both lenses 2/0)
EXCLUDE = {
    "django__django-9296": "Regex false-positive: pure feature request (add Paginator.__iter__); the "
    "gold fix adds a method and prevents no exception. is_crash 'raises' rule fired only on an UNCHANGED "
    "context line 'with self.assertRaises(EmptyPage):' from an unrelated neighboring test; the added "
    "FAIL_TO_PASS test has zero raises, no traceback, no error. Both adversarial lenses voted exclude 2/0. "
    "(User-approved exclusion; the frozen 57 are NOT re-filtered — they keep the same shared-definition "
    "false-positive property, e.g. sympy-12419/xarray-3364, for byte-identical comparability.)",
}


def main():
    audit = json.load(open(AUDIT))
    net_new = audit["verified_net_new"]                 # 76
    confirmed = [i for i in net_new if i not in EXCLUDE]
    out = {
        "name": "benchmark2 crash-half (pre-coverage)",
        "source": "SWE-bench_Verified net-new (disjoint from Lite / the frozen 57)",
        "definition": "single .py gold AND code_gold non-empty AND is_crash(canonical) — byte-identical "
                      "to the frozen-57 predicate. on-path decided later by coverage.",
        "confirmed": confirmed,
        "excluded": [{"instance_id": k, "reason": v} for k, v in EXCLUDE.items()],
        "counts": {"net_new": len(net_new), "excluded": len(EXCLUDE), "confirmed_crash_half": len(confirmed)},
        "audit": {"workflow": "wf_e08f116c-efa", "agents": 44,
                  "code_parity": "byte-identical is_crash; regression gate 57/57; no drift",
                  "onpath_parity": "57/57 reproduced from Lite coverage (raw-region & code_gold, 0 disagreements)",
                  "integrity": "76 net-new, 0 leaks into 57/Lite, all well-formed single-.py-gold, no dupes",
                  "crash_semantics": "14/19 flagged unanimously genuine; 4 borderline kept; 1 unanimous FP excluded"},
    }
    OUT.write_text(json.dumps(out, indent=1))
    print(f"benchmark2 crash-half: {len(confirmed)} confirmed (net-new {len(net_new)} - excluded {len(EXCLUDE)})")
    print(f"  excluded: {list(EXCLUDE)}")
    print(f"  wrote {OUT}")


if __name__ == "__main__":
    main()
