import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _sys.path[:0]=[_d,_os.path.dirname(_d)]; _os.chdir(_os.path.dirname(_d))
#!/usr/bin/env python3
"""M5 offline smoke (NO API): assertion_rerank is recall-safe + falls back; evidence extractor works."""
import json
import region_loc as rl, test_evidence as te, p0_line_recall as p0

lines = [f"line{i}" for i in range(1, 21)]
ranked = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# 1) mock LLM picks "3, 1" → head reordered, set preserved, tail untouched
seen = {}
def fake(model, prompt, **k):
    seen["assert_prompt"] = "FAILING-TEST EVIDENCE" in prompt
    return "root cause: 3, 1"
rl._llm_t = fake
out = rl.assertion_rerank("m", "issue", "f.py", lines, ranked, "the test expected X got Y", top_n=5)
assert seen.get("assert_prompt"), "must use the assertion prompt"
assert set(out) == set(ranked), f"recall-safe (same set) FAILED: {out}"
assert out[:2] == [3, 1], f"head reorder FAILED: {out[:2]}"
assert out[5:] == ranked[5:], f"tail preserved FAILED: {out[5:]}"
print("[1] reorder recall-safe OK:", out)

# 2) empty evidence → unchanged
assert rl.assertion_rerank("m", "i", "f.py", lines, ranked, "", top_n=5) == ranked
# 3) garbage LLM output → fallback to input (never regress)
rl._llm_t = lambda *a, **k: "no numbers"
assert rl.assertion_rerank("m", "i", "f.py", lines, ranked, "ev", top_n=5) == ranked
# 4) LLM error → fallback
def boom(*a, **k): raise RuntimeError("api down")
rl._llm_t = boom
assert rl.assertion_rerank("m", "i", "f.py", lines, ranked, "ev", top_n=5) == ranked
print("[2-4] fallbacks (empty/garbage/error) OK")

# 5) evidence extractor on real S1 instances
rows = {r["instance_id"]: r for r in p0.load_rows(500, dataset="lite")}
sub = json.load(open("rq4/frozen_subsets.json"))["S1_crash_onpath"]
nonempty = 0
for it in sub:
    ev = te.extract_test_evidence(rows[it["instance_id"]])
    if ev: nonempty += 1
print(f"[5] evidence extracted for {nonempty}/{len(sub)} S1 instances")
print("    sample:\n   " + te.extract_test_evidence(rows[sub[1]["instance_id"]])[:240].replace("\n", "\n   "))
assert nonempty >= len(sub) * 0.8, "evidence should be available for most instances"
print("\n✅ ALL M5 SMOKE PASSED — safe to run on GPU")
