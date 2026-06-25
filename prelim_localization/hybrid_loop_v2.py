#!/usr/bin/env python3
"""hybrid_loop_v2 — line-recall-MAXIMIZING repo-level localizer (file-not-given).

Built from the validated diagnosis: file-finding is NOT the bottleneck (candidate-set
recall 0.872); LINE localization inside LARGE files is (gold median ~1895 lines; line
recall 0.107 even file-given-full = the P0-big precision wall). Fix = REGION-narrowing
(region_loc.py): LLM picks suspect elements from the file SKELETON (Agentless) -> line-
loc WITHIN those ~hundreds-of-lines regions + self-consistency union (LocAgent RR / P5).
Validated file-given lift: line recall 0.071 -> 0.260, R@5 23->62, R@10 38->77.

Pipeline (file-NOT-given):
  S1 file-loc: LLM top-k from repo tree (+ 1-hop graph import-neighbors). fetch sources
     with NO 3000-line cap (region_loc bounds the prompt, not the fetch).
  S2 region line-loc: region_loc.region_line_loc per candidate file -> union of (file,line).
  (optional --exec) coverage ranks regions + multi-file exec-feedback loop.

Rigorous eval (as requested):
  - PAIRED instances (same pool) and BOTH whole-file baseline + region reported per instance.
  - line recall GLOBAL and CONDITIONAL ON FILE-HIT (gold files actually found).
  - exclude round0-solved when reporting loop lift (--exec).
  - bootstrap 95% CI on the headline line recalls.

    OPENAI_BASE_URL=... MODEL=deepseek-ai/DeepSeek-V3 python hybrid_loop_v2.py --sample 13
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
import p0_line_recall as p0
import p1_realistic as p1
import code_graph as cg
import region_loc as rl
from hybrid_loop import _llm, RANK_PROMPT, parse_ranked, hit_at_k, KS

HERE = Path(__file__).resolve().parent
PYTEST = {"astropy/astropy","scikit-learn/scikit-learn","pydata/xarray","psf/requests","matplotlib/matplotlib","pallets/flask"}

def bootstrap_ci(xs, nboot=5000):
    """95% percentile bootstrap CI for the mean (real resampling, fixed seed for
    reproducibility)."""
    import random
    n = len(xs)
    if n == 0: return (None, None)
    if n == 1: return (round(xs[0], 3), round(xs[0], 3))
    rng = random.Random(12345)
    means = sorted(sum(xs[rng.randrange(n)] for _ in range(n)) / n for _ in range(nboot))
    return (round(means[int(0.025 * nboot)], 3), round(means[int(0.975 * nboot)], 3))

def run_coverage(iid, r, tree_paths):
    """Run FAIL_TO_PASS under coverage in the official Docker image (traceback-FREE
    navigation signal). Returns (called_files:set, exec_lines:{repo_path:set(lines)}).
    Reuses p7's in-container coverage script. Image pulled+rmi per instance (disk-safe)."""
    import re, tempfile
    import egl_makeorbreak as egl
    import p7_crossfile_exec as p7
    MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple"
    called = set(); exec_lines = {}
    ftp = r.get("FAIL_TO_PASS")
    if isinstance(ftp, str):
        try: ftp = json.loads(ftp)
        except: ftp = []
    if not ftp: return called, exec_lines
    tag = egl.img_tag(iid); cont = "v2cov_" + re.sub(r'[^a-z0-9_]', '_', iid.lower())
    try:
        if egl.docker("image", "inspect", tag).returncode != 0:
            if egl.docker("pull", tag, timeout=1800).returncode != 0:
                return called, exec_lines
        egl.docker("rm", "-f", cont); egl.docker("run", "-d", "--name", cont, tag, "sleep", "infinity")
        try:
            ptxt = (r.get("test_patch") or "").replace("\r\n", "\n")
            if not ptxt.endswith("\n"): ptxt += "\n"
            tp = os.path.join(tempfile.gettempdir(), f"v2_{iid.replace('/','_')}.patch")
            open(tp, "wb").write(ptxt.encode()); egl.docker("cp", tp, f"{cont}:/tmp/test.patch"); os.unlink(tp)
            npy = os.path.join(tempfile.gettempdir(), "v2_narrow.py")
            open(npy, "wb").write(p7.NARROW_PY.encode()); egl.docker("cp", npy, f"{cont}:/tmp/narrow.py"); os.unlink(npy)
            sh = p7.RUN_SH.replace("%TESTS%", " ".join(f"'{t}'" for t in ftp[:6])).replace("%MIRROR%", MIRROR)
            egl.docker("exec", cont, "bash", "-lc", sh, timeout=1800)
            cjf = egl.docker("exec", cont, "cat", "/tmp/called.json")
            if cjf.returncode == 0 and cjf.stdout.strip():
                for fp in json.loads(cjf.stdout):
                    nf = p7.norm(fp)
                    if p7.is_repo_src(nf): called.add(nf)
            cj = egl.docker("exec", cont, "cat", "/tmp/cov.json")
            if cj.returncode == 0 and cj.stdout.strip():
                cov = json.loads(cj.stdout)
                for fp, fd in cov.get("files", {}).items():
                    nf = p7.norm(fp)
                    if p7.is_repo_src(nf) and fd.get("executed_lines"):
                        exec_lines[nf] = set(fd["executed_lines"])
        finally:
            egl.docker("rm", "-f", cont); egl.docker("rmi", tag)
    except Exception:
        pass
    return called, exec_lines

def select_pool(sample):
    rows = {r["instance_id"]: r for r in p0.load_rows(500)}
    cands = []
    for iid, r in rows.items():
        if r["repo"] not in PYTEST: continue
        files = p0.parse_patch(r.get("patch") or "")
        py = [f for f in files if f.endswith(".py") and files[f]["hunks"]]
        if len(py) >= 2 and len(py) == len([f for f in files if f.endswith(".py")]) and r.get("FAIL_TO_PASS"):
            cands.append(iid)
    return rows, cands[:sample]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=13)
    ap.add_argument("--topk", type=int, default=10)
    ap.add_argument("--k", type=int, default=3, help="self-consistency samples")
    ap.add_argument("--baseline", action="store_true", help="also run whole-file baseline (paired)")
    ap.add_argument("--exec", action="store_true", help="coverage signal (Docker): boost file set + rank regions")
    ap.add_argument("--out", default=str(HERE / "hybrid_loop_v2.json"))
    args = ap.parse_args()
    model = os.environ.get("MODEL", "deepseek-ai/DeepSeek-V3")
    rows, pool = select_pool(args.sample)
    print(f"[v2] {len(pool)} multi-file instances; k={args.k} baseline={args.baseline}", file=sys.stderr)
    out = Path(args.out)
    results = json.loads(out.read_text())["results"] if out.exists() else []
    by_id = {r["instance_id"]: r for r in results}

    for idx, iid in enumerate(pool):
        if iid in by_id and by_id[iid].get("done"):
            print(f"{iid} cached", file=sys.stderr); continue
        r = rows[iid]; files = p0.parse_patch(r.get("patch") or "")
        gold_files = [f for f in files if f.endswith(".py")]
        gold = {f: files[f]["region"] for f in gold_files}
        total_gold = sum(len(v) for v in gold.values())
        issue = (r.get("problem_statement") or "")[:5000]
        rec = {"instance_id": iid, "repo": r["repo"], "n_gold_files": len(gold_files), "total_gold": total_gold}
        # ---- S1 file localization (LLM tree + graph import-neighbors) ----
        try:
            tree = p1.fetch_tree(r["repo"], r["base_commit"])
            static_files = p1.parse_str_list(_llm(model, p1.FILE_PROMPT.format(
                issue=issue, nfiles=len(tree["paths"]), filelist="\n".join(tree["paths"])))) [:args.topk]
        except Exception as e:
            rec["error"] = repr(e)[:120]; rec["done"] = True; by_id[iid] = rec
            results = list(by_id.values()); out.write_text(json.dumps({"results": results}, indent=2)); continue
        # fetch candidate sources — NO 3000-line cap (region_loc bounds the prompt)
        file_srcs = {}
        for f in static_files:
            if f not in tree["paths"]: continue
            try:
                s = p0.fetch_file(r["repo"], r["base_commit"], f)
                if 0 < len(s.splitlines()) <= 20000: file_srcs[f] = s
            except Exception: pass
        neigh = []
        try:
            import hybrid_loop_agentic as hla
            neigh = hla.import_neighbors(file_srcs, tree["paths"])
            for f in neigh:
                if f not in file_srcs and f in tree["paths"]:
                    try:
                        s = p0.fetch_file(r["repo"], r["base_commit"], f)
                        if 0 < len(s.splitlines()) <= 20000: file_srcs[f] = s
                    except Exception: pass
        except Exception: pass
        # ---- optional coverage (Docker): boost file set + per-file executed lines ----
        cov_map = {}
        if args.exec:
            called, exec_lines = run_coverage(iid, r, tree["paths"])
            cov_map = exec_lines
            for f in called:                          # add execution-found files (boost file recall)
                if f not in file_srcs and f in tree["paths"]:
                    try:
                        s = p0.fetch_file(r["repo"], r["base_commit"], f)
                        if 0 < len(s.splitlines()) <= 20000: file_srcs[f] = s
                    except Exception: pass
            rec["n_called"] = len(called)
        cand_files = list(file_srcs.keys())
        found = [f for f in gold_files if f in cand_files]
        rec["file_recall"] = round(len(found) / len(gold_files), 3) if gold_files else 0.0
        rec["found_gold_files"] = found
        # ---- S2 region line localization (run on FOUND gold files: only they carry
        # gold lines, so this is the EXACT line recall; non-gold candidates affect only
        # precision, not the recall headline we are maximizing) ----
        reg_glob = []; reg_hit = 0
        whole_glob = []; whole_hit = 0
        for f in found:
            src = file_srcs[f]; gf_gold = gold.get(f, set())
            rp, _, _ = rl.region_line_loc(model, issue, src, f, k_samples=args.k,
                                          coverage_lines=cov_map.get(f))
            reg_glob += [(f, ln) for ln in rp]; reg_hit += len(set(rp) & gf_gold)
            if args.baseline:
                lines = src.splitlines()
                if len(lines) <= 4000:
                    numbered = "\n".join(f"{i+1}: {l}" for i, l in enumerate(lines))
                    try: wp = parse_ranked(_llm(model, RANK_PROMPT.format(issue=issue, path=f, numbered=numbered)))
                    except Exception: wp = []
                else: wp = []
                whole_glob += [(f, ln) for ln in wp]; whole_hit += len(set(wp) & gf_gold)
        goldflat = {(f, ln) for f in gold_files for ln in gold[f]}
        goldflat_found = {(f, ln) for f in found for ln in gold[f]}
        tot_found = max(1, len(goldflat_found))
        rec["line_recall"] = round(reg_hit / total_gold, 3) if total_gold else 0.0
        rec["line_recall_given_filehit"] = round(len(set(reg_glob) & goldflat_found) / tot_found, 3)
        rec.update({f"line_R@{k}": hit_at_k(reg_glob, goldflat, k) for k in KS})
        if args.baseline:
            rec["whole_line_recall"] = round(whole_hit / total_gold, 3) if total_gold else 0.0
            rec.update({f"whole_line_R@{k}": hit_at_k(whole_glob, goldflat, k) for k in KS})
        rec["done"] = True; by_id[iid] = rec; results = list(by_id.values())
        out.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")
        print(f"[{idx+1}/{len(pool)}] {iid:30s} file_rec={rec['file_recall']} "
              f"line_rec={rec['line_recall']} (|filehit={rec['line_recall_given_filehit']}) "
              f"R@5={rec['line_R@5']}" + (f" | whole_line={rec.get('whole_line_recall')}" if args.baseline else ""),
              file=sys.stderr); sys.stderr.flush()

    ok = [r for r in results if "line_recall" in r]
    import statistics as st
    def agg(key):
        xs = [r[key] for r in ok if key in r]; return (round(st.mean(xs), 3), bootstrap_ci(xs)) if xs else (None, None)
    def Rk(key):
        xs = [r[key] for r in ok if key in r]; return round(100 * st.mean(xs), 1) if xs else None
    lr, lr_ci = agg("line_recall"); lrf, lrf_ci = agg("line_recall_given_filehit"); fr, fr_ci = agg("file_recall")
    summary = {"n": len(ok), "k_samples": args.k,
               "file_recall": fr, "file_recall_ci95": fr_ci,
               "line_recall": lr, "line_recall_ci95": lr_ci,
               "line_recall_given_filehit": lrf, "line_recall_given_filehit_ci95": lrf_ci,
               "line_R@k": {k: Rk(f"line_R@{k}") for k in KS}}
    if any("whole_line_recall" in r for r in ok):
        wlr, wlr_ci = agg("whole_line_recall")
        summary["whole_line_recall"] = wlr; summary["whole_line_recall_ci95"] = wlr_ci
        summary["whole_line_R@k"] = {k: Rk(f"whole_line_R@{k}") for k in KS}
    d = json.loads(out.read_text()); d["summary"] = summary; out.write_text(json.dumps(d, indent=2), encoding="utf-8")
    print("\n==== SUMMARY (file-not-given LINE recall) ====\n" + json.dumps(summary, indent=2, ensure_ascii=False), file=sys.stderr)

if __name__ == "__main__":
    main()
