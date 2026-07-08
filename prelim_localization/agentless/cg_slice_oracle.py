#!/usr/bin/env python3
import os as _os, sys as _sys
_HERE=_os.path.dirname(_os.path.abspath(__file__)); _ROOT=_os.path.dirname(_HERE)
_VEND=_os.path.join(_ROOT,"agentless_vendor")
_sys.path[:0]=[_os.path.join(_VEND,"repo"), _ROOT]; _os.chdir(_ROOT)
"""跨文件·覆盖率限定的调用图切片 ORACLE (framing-A, 零 API).
问: 从崩溃帧函数 + 模型高票函数出发, 沿跨文件调用边在【执行函数】上 BFS 到半径K,
    能否把漏掉的金标(尤其82%可达的D类)聚焦进候选池? 代价多少 LoC?
节点=覆盖到的仓库文件里的执行函数; 边=调用名跨文件匹配(over-approx); 种子不看金标(method-plausible).
度量: (模型base池 ∪ K跳切片的执行行) 的 superset & LoC, 扫 K, 对照基线.
  python agentless/cg_slice_oracle.py --tag deepseekv3 [--sample N] [--filecap 90]
"""
import argparse, json, re, statistics as st
from collections import defaultdict, deque
import p0_line_recall as p0
import code_graph as cg
import agentless.al_vote_eval as E
import agentless.al_baseline_native as NB

FRAME_RE=re.compile(r'\bin\s+([A-Za-z_][A-Za-z0-9_]*)')
def frame_names(cctx):
    return set(FRAME_RE.findall(cctx or ""))

def repo_file(f):
    return not (f.startswith("/") or "site-packages" in f or f.startswith("usr/") or "/lib/python" in f)

def build_graph(iid, r, cm, ff, vote_funcs_files, filecap):
    """解析覆盖到的仓库文件 -> 执行函数节点 + 跨文件调用边. 返回 nodes, name_idx, edges, exec_lines_of."""
    files=[f for f in cm if repo_file(f)]
    # 优先: found_files + 有崩溃帧名/高票的文件 + 执行行多的文件
    files=sorted(files, key=lambda f:(-(f in ff), -len(cm[f])))[:filecap]
    nodes={}          # (file,fname,start,end) key -> dict
    name_idx=defaultdict(set)
    exec_of={}        # node_key -> set(executed lines in span)
    src_cache={}
    for f in files:
        try: src=p0.fetch_file(r["repo"], r["base_commit"], f)
        except Exception: continue
        src_cache[f]=src
        try: g=cg.CodeGraph(src, f)
        except Exception: g=None
        if not g or not g.ok: continue
        exlines=set(int(x) for x in cm.get(f,[]))
        for fn in g.funcs:
            a,b=fn["start"],fn["end"]; span=set(range(a,b+1))
            ex=span & exlines
            if not ex: continue                       # 只保留执行函数
            key=(f, fn["name"], a, b)
            nodes[key]=dict(file=f, name=fn["name"], cls=fn.get("class"), start=a, end=b, calls=set(fn.get("calls",[])))
            exec_of[key]=ex
            name_idx[fn["name"]].add(key)
    # 调用边 (name-based, 跨文件): F -> def(callee-name)
    fwd=defaultdict(set); bwd=defaultdict(set)
    for k,nd in nodes.items():
        for cal in nd["calls"]:
            for tgt in name_idx.get(cal, ()):
                if tgt!=k: fwd[k].add(tgt); bwd[tgt].add(k)
    return nodes, name_idx, fwd, bwd, exec_of

def bfs_depth(seeds, fwd, bwd, K):
    """双向 BFS, 返回 {node: hop} for hop<=K."""
    dist={s:0 for s in seeds}; q=deque(seeds)
    while q:
        u=q.popleft(); d=dist[u]
        if d>=K: continue
        for v in fwd.get(u,set()) | bwd.get(u,set()):
            if v not in dist: dist[v]=d+1; q.append(v)
    return dist

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--tag",required=True)
    ap.add_argument("--sample",type=int,default=0); ap.add_argument("--filecap",type=int,default=90)
    a=ap.parse_args()
    unc=json.load(open(f"agentless/al_baseline_cache_{a.tag}.json"))
    sub=json.load(open(_os.environ["EGL_SUBSET_FILE"])) if _os.environ.get("EGL_SUBSET_FILE") else json.load(open("rq3_subsets.json"))["crash_onpath"]
    if a.sample: sub=sub[:a.sample]
    rows={r["instance_id"]:r for r in p0.load_rows(500,dataset=_os.environ.get("SWEBENCH_DATASET","lite"))}
    cov=json.load(open(_os.environ.get("EGL_COV_FILE","egl_cov_cache.json")))
    KS=[0,1,2,3]
    agg={K:{"A":[],"L":[],"frac":[]} for K in KS}; baseA=[]; baseL=[]; nseed0=0; n=0
    miss_reached={K:0 for K in KS}; miss_tot=0            # 漏金标行(可达执行的)被切片覆盖计数
    for iid in sub:
        r=rows.get(iid); cm=cov.get(iid); su=unc.get(iid)
        if not r or not cm or iid not in E.LOC or not su: continue
        gold=E.gold_pairs(r)
        if not gold: continue
        base=NB.native_pairs(iid,r,su)
        ff=E.LOC[iid]["found_files"][:NB.TOP_N]
        vote_files=set(f for (f,ln) in base)
        nodes,name_idx,fwd,bwd,exec_of=build_graph(iid,r,cm,ff,vote_files,a.filecap)
        fnames=frame_names(E._crash_ctx(r))
        seeds=set()
        for k,nd in nodes.items():
            if nd["name"] in fnames: seeds.add(k)
        for (f,ln) in base:
            for k,ex in exec_of.items():
                if k[0]==f and k[2]<=ln<=k[3]: seeds.add(k)
        if not seeds: nseed0+=1
        n+=1
        g=set(gold); missed=g-set(base)
        baseA.append(1 if g<=set(base) else 0); baseL.append(len(set(base)))
        miss_tot+=len(missed)
        for K in KS:
            dist=bfs_depth(seeds,fwd,bwd,K)
            slice_lines=set()
            for k in dist:
                for ln in exec_of[k]: slice_lines.add((k[0],ln))
            pool=set(base)|slice_lines
            agg[K]["A"].append(1 if g<=pool else 0); agg[K]["L"].append(len(pool))
            reached=sum(1 for m in missed if m in slice_lines)
            agg[K]["frac"].append(reached/len(missed) if missed else 1.0)
            miss_reached[K]+=reached
    print(f"\n===== {a.tag} 跨文件调用图切片 oracle (n={n}, 无种子例={nseed0}, filecap={a.filecap}) =====")
    bs=100*st.mean(baseA); bl=st.mean(baseL)
    print(f"  基线(model base池, ±10)      : superset={bs:.1f}  LoC={bl:.0f}  (漏金标总{miss_tot}行)")
    print(f"  {'K跳':>4}{'superset':>10}{'LoC':>8}{'Δsup':>8}{'漏金标被覆盖':>14}")
    for K in KS:
        s=100*st.mean(agg[K]["A"]); l=st.mean(agg[K]["L"])
        mr=100*miss_reached[K]/max(miss_tot,1)
        print(f"  {K:>4}{s:>10.1f}{l:>8.0f}{s-bs:>+8.1f}{f'{miss_reached[K]}/{miss_tot}={mr:.0f}%':>14}")
    print("  (切片按执行行计入池; 漏金标被覆盖=切片够到的漏金标行比例; 目标=聚焦=高覆盖&低LoC)")

if __name__=="__main__": main()
