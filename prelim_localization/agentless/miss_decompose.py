#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_VEND=_os.path.join(_ROOT,"agentless_vendor")
_sys.path[:0]=[_os.path.join(_VEND,"repo"), _ROOT]; _os.chdir(_ROOT)
"""归因: 基线(no-expand10)漏掉的金标行, 分类 => 二次判别为何救不回.
  D  = 金标在 found_files 之外 (file-loc 漏, 二次判别只看 found_files, 够不到)
  C/A= 金标在 found_files 内:
        - 已执行 (executed)         -> 原则上二次判别看得到 (A看见没选 / C其他执行函数)
        - 未执行但±2内              -> 边界
        - 离执行>±2                 -> 覆盖率信号弱
对每个漏金标实例逐条统计, 汇总占比. 判断 rediscr 天花板.
"""
import argparse, json
import p0_line_recall as p0
import agentless.al_vote_eval as E
import agentless.al_baseline_native as NB

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--tag",required=True); a=ap.parse_args()
    unc=json.load(open(f"agentless/al_baseline_cache_{a.tag}.json"))
    sub=json.load(open(_os.environ["EGL_SUBSET_FILE"])) if _os.environ.get("EGL_SUBSET_FILE") else json.load(open("rq3_subsets.json"))["crash_onpath"]
    rows={r["instance_id"]:r for r in p0.load_rows(500,dataset=_os.environ.get("SWEBENCH_DATASET","lite"))}
    cov=json.load(open(_os.environ.get("EGL_COV_FILE","egl_cov_cache.json")))
    tot={"D_outfile":0,"C_infile_exec":0,"infile_adj2":0,"infile_far":0}
    miss_inst=0; nmiss_all=0; recoverable_inst=0
    for iid in sub:
        r=rows.get(iid); cm=cov.get(iid); su=unc.get(iid)
        if not r or not cm or iid not in E.LOC or not su: continue
        gold=E.gold_pairs(r)
        if not gold: continue
        base=NB.native_pairs(iid,r,su)            # no-expand10 基线覆盖行
        missed=set(gold)-set(base)                # 基线漏掉的金标行 (no-expand10)
        if not missed: continue
        miss_inst+=1; nmiss_all+=len(missed)
        ff=set(E.LOC[iid]["found_files"][:NB.TOP_N])
        ecache={}
        cls={"D_outfile":0,"C_infile_exec":0,"infile_adj2":0,"infile_far":0}
        for (f,ln) in missed:
            if f not in ff: cls["D_outfile"]+=1; continue
            if f not in ecache: ecache[f]=E.cov_for(f,cm)
            ex=ecache[f]
            if ln in ex: cls["C_infile_exec"]+=1
            elif any((ln+d) in ex for d in (-2,-1,1,2)): cls["infile_adj2"]+=1
            else: cls["infile_far"]+=1
        for k in tot: tot[k]+=cls[k]
        # 该实例是否"理论可救"= 漏掉的金标全部在found_files内且执行/邻近 (二次判别够得到)
        if cls["D_outfile"]==0 and cls["infile_far"]==0: recoverable_inst+=1
    print(f"\n===== {a.tag}  基线漏金标归因 (no-expand10) =====")
    print(f"  漏金标实例: {miss_inst}   漏金标行总数: {nmiss_all}")
    if nmiss_all:
        for k in ["D_outfile","C_infile_exec","infile_adj2","infile_far"]:
            print(f"    {k:>16}: {tot[k]:>4}  ({100*tot[k]/nmiss_all:.0f}%)")
    print(f"  '理论可被二次判别救回'的实例(漏金标全部 in-file 且 执行/±2): {recoverable_inst}/{miss_inst}")
    print(f"  => 二次判别 superset 天花板 ≈ 基线 + {recoverable_inst}例 (若模型二次判别100%成功)")

if __name__=="__main__": main()
