import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _sys.path[:0]=[_d,_os.path.dirname(_d)]; _os.chdir(_os.path.dirname(_d))
#!/usr/bin/env python3
"""RQ4 single driver (THE only entrypoint; everything else is read-only data). Resumable & idempotent:
every sub-run writes a per-instance JSON that egl_e2e resumes; a finished sub-run (has 'summary') is
skipped. Tasks:
  --task fileloc : Task1 — sweep file-loc on n=300, pick first config hitting ARISE (R@1>=67 & R@3>=82)
  --task e2e     : Task2 — run the winning file-loc on S1, then PASS_A + PASS_B; assemble M0..M4 arms
  --task sig     : cross-pass paired bootstrap CI of the RQ4 headline (M4 - M0) on S1
  --verify       : completeness report + summary table
Usage (on the A800 box, under tmux — see rq4/launch.sh):
  python rq4/run_all.py --task fileloc && python rq4/run_all.py --task e2e \
    && python rq4/run_all.py --task sig && python rq4/run_all.py --verify"""
import argparse, json, subprocess, random, statistics as st
import rq4.config as C

PY = _sys.executable
os = _os
os.makedirs(C.RESULTS, exist_ok=True)

def log(m): print(f"[run_all] {m}", flush=True)
def complete(out):
    try: return "summary" in json.loads(open(out).read())
    except Exception: return False
def summ(out): return json.loads(open(out).read()).get("summary", {})
def recs(out): return json.loads(open(out).read()).get("results", [])

def write_s1_ids():
    s1 = json.load(open(C.FROZEN))["S1_crash_onpath"]
    ids = [x["instance_id"] for x in s1]
    json.dump({"instances": ids}, open(C.S1_IDS, "w"), indent=1)
    return ids

def make_oracle_reuse():
    """file-given: hand each S1 instance its GOLD file as the only ranked file → egl_e2e skips file-loc
    (--reuse-files reads {iid: ranked_files}); isolates the line-loc step from file-loc entirely."""
    s1 = json.load(open(C.FROZEN))["S1_crash_onpath"]
    res = [{"instance_id": x["instance_id"], "ranked_files": [x["gold_file"]]} for x in s1]
    json.dump({"results": res}, open(C.ORACLE_REUSE, "w"), indent=1)
    return C.ORACLE_REUSE

def egl(out, extra, sample=None, instances=None, reuse=None, k=None):
    """One egl_e2e sub-run (resumes via its own --out). Returns when complete."""
    if complete(out):
        log(f"skip (done): {os.path.basename(out)}"); return
    cmd = [PY, "egl_e2e.py", "--out", out, "--k", str(k or C.K), "--topk", str(C.TOPK),
           "--workers", str(C.WORKERS), "--cov-workers", str(C.COV_WORKERS)]
    if C.ARISE_GOLD: cmd += ["--arise-gold"]
    if sample is not None: cmd += ["--sample", str(sample), "--broad"]
    if instances: cmd += ["--instances", instances]
    if reuse: cmd += ["--reuse-files", reuse]
    cmd += extra
    env = dict(os.environ, MODEL=C.MODEL, OPENAI_BASE_URL=C.BASE_URL, SWEBENCH_DATASET="lite")
    log("RUN: " + " ".join(cmd))
    subprocess.run(cmd, env=env, check=True)

# ---------------- Task 1: file-loc sweep ----------------
def task_fileloc():
    sweep = {}
    for name, flags in C.FILELOC_SWEEP:
        out = os.path.join(C.RESULTS, f"fileloc_{name}.json")
        egl(out, flags, sample=300, k=1)                 # full Lite; k=1 keeps line-loc cheap (file R@k unaffected)
        fr = summ(out).get("file_R@k", {})
        sweep[name] = {"file_R@k": fr, "out": out}
        log(f"  {name}: file R@1={fr.get('1')} R@3={fr.get('3')} R@5={fr.get('5')} R@10={fr.get('10')}")
    winner = next((n for n in sweep if (sweep[n]["file_R@k"].get("1") or 0) >= C.FILELOC_TARGET["R@1"]
                   and (sweep[n]["file_R@k"].get("3") or 0) >= C.FILELOC_TARGET["R@3"]), None)
    if not winner:
        winner = max(sweep, key=lambda n: sweep[n]["file_R@k"].get("3") or 0)
        log(f"⚠ no config hit ARISE parity; best-by-R@3 = {winner} (report gap)")
    else:
        log(f"✓ ARISE parity hit by: {winner}")
    open(os.path.join(C.RESULTS, "FILELOC_FROZEN.txt"), "w").write(winner)
    json.dump({"target": C.FILELOC_TARGET, "sweep": sweep, "winner": winner},
              open(os.path.join(C.RESULTS, "fileloc_sweep.json"), "w"), indent=1)
    log(f"→ FILELOC_FROZEN = {winner}  (results/fileloc_sweep.json)")

# ---------------- Task 2: RQ4 e2e on S1 ----------------
def task_e2e():
    ids = write_s1_ids(); log(f"S1 frozen pool: {len(ids)} instances (file-given / oracle gold file)")
    reuse = make_oracle_reuse()                          # file-given: gold file handed in → file-loc skipped
    for passname, pflags in C.RQ4_PASSES.items():
        egl(os.path.join(C.RESULTS, f"{passname}.json"), pflags, instances=C.S1_IDS, reuse=reuse)
    # assemble M0..M5 from all passes' arm metrics
    P = {pn: {r["instance_id"]: r for r in recs(os.path.join(C.RESULTS, f"{pn}.json"))} for pn in C.RQ4_PASSES}
    table = {}
    for arm, (passname, egl_arm) in C.RQ4_ARM_MAP.items():
        src = P.get(passname, {})
        vals = [rr["arms"][egl_arm] for rr in src.values() if rr.get("arms", {}).get(egl_arm)]
        if vals:
            table[arm] = {f"R@{k}": round(100*st.mean([v[f"R@{k}"] for v in vals]), 1) for k in (1,5,10)}
    json.dump({"config": C.env_banner(), "file_loc": "oracle(gold-file, file-given)", "n_S1": len(ids),
               "arms": table, "arise_ref_NOTE": "ARISE 41/62/74 is END-TO-END口径; NOT comparable to these file-given absolutes",
               "arise_ref": C.ARISE_REF, "offline_ceiling": C.OFFLINE_FILTER_CEILING},
              open(os.path.join(C.RESULTS, "lineloc_e2e.json"), "w"), indent=1)
    log("→ results/lineloc_e2e.json")
    for a, m in table.items(): log(f"  {a:22s} R@1={m['R@1']:5} R@5={m['R@5']:5} R@10={m['R@10']:5}")

# ---------------- Task 3: significance ----------------
def task_sig():
    P = {pn: {r["instance_id"]: r for r in recs(os.path.join(C.RESULTS, f"{pn}.json"))} for pn in C.RQ4_PASSES}
    def arm_hits(src, egl_arm, k):
        return {iid: rr["arms"][egl_arm][f"R@{k}"] for iid, rr in src.items() if rr.get("arms", {}).get(egl_arm)}
    def boot(dmap, N=C.BOOT_N, seed=12345):
        d = list(dmap.values()); n = len(d)
        if n < 2: return {"delta_pp": round(100*(d[0] if d else 0),1), "ci95": None, "sig": False, "n": n}
        rng = random.Random(seed); pt = 100*st.mean(d)
        bs = sorted(100*st.mean([d[rng.randrange(n)] for _ in range(n)]) for _ in range(N))
        lo, hi = bs[int(0.025*N)], bs[int(0.975*N)]
        return {"delta_pp": round(pt,1), "ci95": [round(lo,1), round(hi,1)], "sig": bool(lo>0 or hi<0), "n": n}
    out = {"primary": C.PRIMARY_DELTA, "deltas": {}}
    pairs = {"M4_minus_M0": (("passB_covnarrow","ours_dynamic"), ("passA_normal","ours_static")),
             "M2_minus_M0": (("passB_covnarrow","ours_static"),  ("passA_normal","ours_static")),
             "M3_minus_M0": (("passA_normal","ours_dynamic"),    ("passA_normal","ours_static")),
             "M5_minus_M0": (("passC_m5","ours_m5"),             ("passA_normal","ours_static")),
             "M5_minus_M4": (("passC_m5","ours_m5"),             ("passB_covnarrow","ours_dynamic"))}
    for name, ((ps_a, arm_a), (ps_b, arm_b)) in pairs.items():
        sa = P.get(ps_a, {}); sb = P.get(ps_b, {})
        out["deltas"][name] = {}
        for k in (1, 5, 10):
            ha, hb = arm_hits(sa, arm_a, k), arm_hits(sb, arm_b, k)
            common = set(ha) & set(hb)
            out["deltas"][name][f"R@{k}"] = boot({i: ha[i]-hb[i] for i in common})
    json.dump(out, open(os.path.join(C.RESULTS, "significance.json"), "w"), indent=1)
    log("→ results/significance.json")
    for name, dd in out["deltas"].items():
        for k, v in dd.items():
            log(f"  {name} {k}: Δ={v['delta_pp']:+}pp CI={v['ci95']} {'SIG' if v['sig'] else 'ns'} (n={v['n']})")

# ---------------- verify ----------------
def verify():
    need = ["oracle_files_S1.json", "passA_normal.json", "passB_covnarrow.json",
            "lineloc_e2e.json", "significance.json"]   # file-given main path (fileloc_* are optional/Task1)
    log("completeness:")
    for f in need:
        p = os.path.join(C.RESULTS, f); ok = os.path.exists(p) and (not f.endswith(".json") or complete(p) or f in ("fileloc_sweep.json","lineloc_e2e.json","significance.json"))
        log(f"  [{'x' if os.path.exists(p) else ' '}] {f}")
    if os.path.exists(os.path.join(C.RESULTS, "lineloc_e2e.json")):
        log("RQ4 table:\n" + json.dumps(json.load(open(os.path.join(C.RESULTS,"lineloc_e2e.json"))).get("arms",{}), indent=1, ensure_ascii=False))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", choices=["fileloc", "e2e", "sig"]); ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    log(C.env_banner())
    if a.verify: verify()
    elif a.task == "fileloc": task_fileloc()
    elif a.task == "e2e": task_e2e()
    elif a.task == "sig": task_sig()
    else: ap.print_help()
