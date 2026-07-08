#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_sys.path[:0]=[_ROOT]; _os.chdir(_ROOT)
"""独立严格审核: 把【57 例的确切选取逻辑】(rq4/freeze_subsets.py) 逐字施加到 benchmark2 的 61 个 Verified 实例,
从原始 issue/patch/覆盖率重新推导, 不信任 benchmark2 存的 crash_rule/n_gold_executed 字段.

通过 = 每个实例都 (a) is_crash 为真 (同 57 的 TB/FRAME2/RAISES 规则)
              (b) on-path 为真 (57 口径: parse_patch region-gold ∩ 失败测试覆盖率 ≥1)
              (c) issue 非空 (格式)
并交叉核对: 重新推导的 first-.py-gold-file 是否 = benchmark2 存的 gold_file.
"""
import json, re
import p0_line_recall as p0

TB = re.compile(r"Traceback \(most recent call last\)")
FRAME2 = re.compile(r'File "[^"]+", line \d+')
RAISES = re.compile(r"pytest\.raises|assertRaises|with\s+raises|\.raises\(")
def is_crash(i, t):
    i = i or ""; return bool(TB.search(i)) or len(FRAME2.findall(i)) >= 2 or bool(RAISES.search(t or ""))
def cov_for(f, cm):
    if f in cm: return set(cm[f])
    for cf, cl in cm.items():
        if cf.endswith(f) or f.endswith(cf.split("/")[-1]): return set(cl)
    return set()

b2 = json.load(open("newbench/benchmark2.json"))["benchmark2_crash_onpath"]
rows = {r["instance_id"]: r for r in p0.load_rows(500, dataset="verified")}
cov = json.load(open("newbench/verified_cov_cache.json"))

fail_crash=[]; fail_onpath=[]; fail_issue=[]; fail_row=[]; gf_mismatch=[]; rule_recheck={}
ok=0
for x in b2:
    iid=x["instance_id"]; r=rows.get(iid); cm=cov.get(iid)
    if not r: fail_row.append(iid); continue
    issue=r.get("problem_statement"); tp=r.get("test_patch")
    # (a) is_crash 独立重跑
    crash = is_crash(issue, tp)
    if not crash: fail_crash.append(iid)
    # 记录命中的规则(独立)
    rule = "traceback" if TB.search(issue or "") else ("frames>=2" if len(FRAME2.findall(issue or ""))>=2 else ("raises" if RAISES.search(tp or "") else "NONE"))
    rule_recheck[iid]=rule
    # (b) on-path 独立重推 (57 口径: region-gold ∩ cov)
    gf = p0.parse_patch(r.get("patch") or "")
    picked=None
    for f in [k for k in gf if k.endswith(".py")]:
        gold=sorted(set(gf[f]["region"]))
        if not gold: continue
        ex=cov_for(f, cm) if cm else set()
        if not ex: continue
        picked=(f, gold, ex); break
    onpath = bool(set(picked[1]) & picked[2]) if picked else False
    if not onpath: fail_onpath.append(iid)
    # (c) issue 格式非空
    if not (issue or "").strip(): fail_issue.append(iid)
    # 交叉核对 gold_file
    if picked and picked[0]!=x.get("gold_file"): gf_mismatch.append((iid, picked[0], x.get("gold_file")))
    if crash and onpath and (issue or "").strip(): ok+=1

from collections import Counter
print(f"==== benchmark2 独立严格审核 (vs 57 确切定义), n={len(b2)} ====")
print(f"  全通过 (is_crash ∧ on-path ∧ issue非空): {ok}/{len(b2)}")
print(f"  ✗ is_crash 不满足 : {len(fail_crash)}  {fail_crash[:8]}")
print(f"  ✗ on-path 不满足  : {len(fail_onpath)}  {fail_onpath[:8]}")
print(f"  ✗ issue 空/格式    : {len(fail_issue)}  {fail_issue[:8]}")
print(f"  ✗ Verified 行缺失  : {len(fail_row)}  {fail_row[:8]}")
print(f"  gold_file 重推≠存储: {len(gf_mismatch)}  {gf_mismatch[:5]}")
print(f"  独立 crash 规则分布: {dict(Counter(rule_recheck.values()))}")
# 与存储的 crash_rule 对比
stored={x['instance_id']:x.get('crash_rule') for x in b2}
disagree=[(i,rule_recheck[i],stored[i]) for i in rule_recheck if rule_recheck[i]!=stored[i]]
print(f"  独立规则 vs 存储 crash_rule 不一致: {len(disagree)}  {disagree[:5]}")
