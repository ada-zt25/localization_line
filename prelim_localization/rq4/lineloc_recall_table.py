import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _sys.path[:0]=[_d,_os.path.dirname(_d)]; _os.chdir(_os.path.dirname(_d))
#!/usr/bin/env python3
"""RQ4 总召回表 (fraction recall) — 纯本地，从 passA/passB 的 per-instance 分臂指标聚合。
fraction recall = 召回的金标行 / 全部金标行 (file-given，所以 = recall-given-found-file)。
顺带报 precision / F1 / 候选宽度(n_pred)，并对 M4−M0 的 recall 做配对 bootstrap 95% CI。"""
import json, random, statistics as st
import rq4.config as C

def recs(name): return json.load(open(_os.path.join(C.RESULTS, name))).get("results", [])
PA = {r["instance_id"]: r for r in recs("passA_normal.json")}
PB = {r["instance_id"]: r for r in recs("passB_covnarrow.json")}
def src(pn): return PA if pn == "passA_normal" else PB
def vals(pn, ea, key):
    return {i: rr["arms"][ea][key] for i, rr in src(pn).items() if rr.get("arms", {}).get(ea)}

METRICS = ["recall", "precision", "f1", "n_pred"]
table = {}
for arm, (pn, ea) in C.RQ4_ARM_MAP.items():
    row = {}
    for m in METRICS:
        v = list(vals(pn, ea, m).values()); row[m] = round(st.mean(v), 3) if v else None
    table[arm] = row

def boot(dmap, N=C.BOOT_N, seed=12345):
    d = list(dmap.values()); n = len(d)
    if n < 2: return {"delta": round(d[0], 3) if d else 0, "ci95": None, "sig": False, "n": n}
    rng = random.Random(seed); pt = st.mean(d)
    bs = sorted(st.mean([d[rng.randrange(n)] for _ in range(n)]) for _ in range(N))
    lo, hi = bs[int(0.025*N)], bs[int(0.975*N)]
    return {"delta": round(pt, 3), "ci95": [round(lo, 3), round(hi, 3)], "sig": bool(lo > 0 or hi < 0), "n": n}
def pair_delta(metric):
    a = vals("passB_covnarrow", "ours_dynamic", metric); b = vals("passA_normal", "ours_static", metric)
    common = set(a) & set(b); return boot({i: a[i]-b[i] for i in common})

sig = {m: pair_delta(m) for m in ("recall", "precision", "f1")}

# ---- print ----
LABEL = {"M0_ours_static": "M0 ours-static (无覆盖)", "M3_ours_dynamic": "M3 +覆盖打分项",
         "M2_covnarrow_static": "M2 +覆盖收窄投票", "M4_coverage_max": "M4 coverage-max",
         "anchor_arise_static": "(锚) arise-static 纯静态", "anchor_vote_only": "(锚) vote-only"}
print("RQ4 行级定位【总召回 fraction recall】表  (crash on-path, n=57, file-given, 完整流水线, Qwen2.5-Coder-32B)\n")
hd = f"{'臂':<26}{'总召回':>9}{'精度':>9}{'F1':>8}{'候选行数':>10}"
print(hd); print("-"*len(hd))
for arm in C.RQ4_ARM_MAP:
    r = table[arm]
    print(f"{LABEL[arm]:<26}{r['recall']:>9.3f}{r['precision']:>9.3f}{r['f1']:>8.3f}{r['n_pred']:>10.1f}")
print("\n=== 主结论 M4 − M0（配对 bootstrap 95% CI, 10000 重采样）===")
for m in ("recall", "precision", "f1"):
    s = sig[m]; star = "  *** 显著(CI不含0)" if s["sig"] else "  (含0)"
    print(f"  Δ{m:<10} = {s['delta']:+.3f}   95%CI {s['ci95']}{star}")

out = {"setup": "crash on-path, n=57, file-given(oracle), full vote+graph+LLM, Qwen2.5-Coder-32B",
       "metric_note": "recall = fraction recall = 召回金标行/全部金标行 (file-given → = recall-given-found-file)",
       "arms": table, "M4_minus_M0": sig, "model": C.MODEL}
json.dump(out, open(_os.path.join(C.RESULTS, "lineloc_recall.json"), "w"), indent=1, ensure_ascii=False)
print("\n→ 写出 rq4/results/lineloc_recall.json")
