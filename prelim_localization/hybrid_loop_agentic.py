#!/usr/bin/env python3
"""hybrid_loop_agentic — Experiment 2: the hybrid_loop method in the REAL agentic
setting (repository-level, file NOT given). Where the old P8 ran single-file/file-given
(static already ceilings), here the system must navigate a ~1600-file repo to find
file -> function -> line, then run the execution-feedback loop. This is where the
ARISE-style code graph pays off and where static has headroom (RP §6 next step).

Per multi-file pytest-native instance, three stages (one Docker container, reused):

  S1 file localization (file-not-given):
       static  = LLM top-k from the repo .py list           (p1.FILE_PROMPT)
       +called = ∪ files whose FUNCTION BODIES executed       (p7 called-coverage)
       +graph  = code_graph.rank_files re-ranks (static∪called) by issue relevance
                 + structure (defines an issue symbol)        -> candidate file set
  S2 line localization within candidate gold files (file given = candidate set):
       static  vs  graph-augmented ranked lines (skeleton + def-use slice)
                 -> global line recall over ALL gold lines
  S3 exec-feedback loop (the agentic hybrid_loop), --loop:
       propose MULTI-FILE SEARCH/REPLACE edits over candidate files -> run
       FAIL_TO_PASS -> the failure traceback RE-SEEDS the candidate set (newly named
       repo files added) -> iterate K rounds. Localization = union of (file,line),
       ranked globally by graph suspiciousness.

Metrics: file-recall@k, all-files-found, global line-recall, Line Recall@k (ARISE),
context-efficiency (#predicted). Compare to p2 (static multi-file) and p7 (called-cov).

    OPENAI_BASE_URL=https://api.siliconflow.com/v1 MODEL=deepseek-ai/DeepSeek-V3 \
        python hybrid_loop_agentic.py --sample 13 --rounds 4
        python hybrid_loop_agentic.py --sample 13 --no-exec   # S1-static+graph + S2 (no Docker)
"""
from __future__ import annotations
import argparse, json, os, re, sys, tempfile, time
from pathlib import Path
import p0_line_recall as p0
import p1_realistic as p1
import p7_crossfile_exec as p7
import egl_makeorbreak as egl
import code_graph as cg
from hybrid_loop import _llm, EDIT_FMT, parse_ranked, hit_at_k, KS, RANK_PROMPT

HERE = Path(__file__).resolve().parent
MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple"
PYTEST = p7.PYTEST

# ---- multi-file edit format (path-tagged) -----------------------------------
MF_EDIT_FMT = """Output one or more EDIT BLOCKS, each in EXACTLY this format (note the file= tag):
<<<<<<< SEARCH file=path/to/file.py
(exact consecutive lines copied verbatim from that file above, WITHOUT the "N: " prefix)
=======
(the replacement lines)
>>>>>>> REPLACE
The SEARCH text must match the file byte-for-byte. Output ONLY edit blocks, no commentary."""

REPAIR_MF = """You are fixing a GitHub issue that may span SEVERAL files in a repository.

## Issue
{issue}
{failblock}
## Candidate files (structure + numbered source)
{files}

## Task
Find ALL decisive locations across these files and produce the minimal edit(s). """ + MF_EDIT_FMT

LINE_PROMPT_G = """You are localizing the exact lines to edit in ONE file to resolve a GitHub issue.

## Issue
{issue}

{graph}
## File: {path}
{numbered}

## Task
List the line numbers MOST LIKELY to need editing, RANKED most-likely first, up to 15.
Output ONLY a JSON array of line numbers. JSON only."""

def import_neighbors(file_srcs, tree_paths, max_add=10):
    """Graph NAVIGATION (additive): repo files imported by the candidate files (1-hop
    import edges). The LLM file-ranker is already strong, so the graph ADDS structurally-
    connected files it may have missed rather than re-ranking/truncating its picks."""
    import ast as _ast
    mod2path = {}
    for p in tree_paths:
        m = p[:-3].replace("/", ".")
        if m.endswith(".__init__"): m = m[:-9]
        mod2path[m] = p
    add = set()
    for path, src in file_srcs.items():
        try: t = _ast.parse(src)
        except Exception: continue
        mods = set()
        for n in _ast.walk(t):
            if isinstance(n, _ast.Import):
                for a in n.names: mods.add(a.name)
            elif isinstance(n, _ast.ImportFrom) and n.module:
                mods.add(n.module)
                for a in n.names: mods.add(n.module + "." + a.name)
        for m in mods:
            if m in mod2path and mod2path[m] not in file_srcs:
                add.add(mod2path[m])
    return sorted(add)[:max_add]

def parse_mf_edits(text):
    """[(path, search, replace)] from path-tagged SEARCH/REPLACE blocks."""
    return re.findall(
        r"<<<<<<< SEARCH file=([^\n]+?)\s*\n(.*?)\n=======\s*\n(.*?)\n>>>>>>> REPLACE",
        text, re.S)

def _deprefix(block):
    return "\n".join(re.sub(r'^\s*\d+:\s?', '', ln) for ln in block.split("\n"))

def apply_mf_edits(srcs, edits):
    """srcs={path:content}. Returns (new_srcs, edited={path:set(lines)})."""
    new = dict(srcs); edited = {}
    for path, search, replace in edits:
        path = path.strip()
        if path not in new or not search.strip():
            continue
        orig = new[path]
        for s, rep in ((search, replace), (_deprefix(search), _deprefix(replace))):
            if s in orig:
                idx = orig.find(s); start = orig.count("\n", 0, idx) + 1
                end = start + s.count("\n")
                edited.setdefault(path, set()).update(range(start, end + 1))
                new[path] = orig.replace(s, rep, 1)
                break
    return new, edited

def numbered_block(path, src, graph_cands, max_body=320):
    """One candidate file's prompt block: skeleton + numbered source (capped)."""
    g = cg.CodeGraph(src, path)
    lines = src.splitlines()
    head = f"### File: {path} ({len(lines)} lines)\n{g.skeleton(max_funcs=25)}\n"
    cand = ", ".join(f"L{c}" for c in graph_cands.get(path, [])[:12])
    if cand: head += f"# data-flow candidate lines: {cand}\n"
    if len(lines) <= max_body:
        body = "\n".join(f"{i+1}: {ln}" for i, ln in enumerate(lines))
    else:  # show graph-candidate neighborhoods only, for big files
        keep = set()
        for c in graph_cands.get(path, []):
            keep |= set(range(max(1, c - 8), min(len(lines), c + 8) + 1))
        body = "\n".join(f"{i+1}: {lines[i]}" for i in range(len(lines)) if (i + 1) in keep) or "(large file; see candidates)"
    return head + body

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=13)
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--topk", type=int, default=10)
    ap.add_argument("--loop-files", type=int, default=4, help="max files editable in the loop")
    ap.add_argument("--max-file-lines", type=int, default=800)
    ap.add_argument("--no-loop", action="store_true")
    ap.add_argument("--no-exec", action="store_true", help="skip ALL Docker (S1-static+graph + S2)")
    ap.add_argument("--keep-images", action="store_true")
    ap.add_argument("--out", default=str(HERE / "hybrid_loop_agentic.json"))
    args = ap.parse_args()
    model = os.environ.get("MODEL", "deepseek-ai/DeepSeek-V3")

    rows = {r["instance_id"]: r for r in p0.load_rows(500)}
    cands = []
    for iid, r in rows.items():
        if r["repo"] not in PYTEST: continue
        files = p0.parse_patch(r.get("patch") or "")
        py = [f for f in files if f.endswith(".py") and files[f]["hunks"]]
        if len(py) >= 2 and len(py) == len([f for f in files if f.endswith(".py")]) and r.get("FAIL_TO_PASS"):
            cands.append(iid)
    cands = cands[:args.sample]
    print(f"[agentic] {len(cands)} multi-file instances; loop={not args.no_loop} exec={not args.no_exec}", file=sys.stderr)

    out = Path(args.out)
    results = json.loads(out.read_text())["results"] if out.exists() else []
    by_id = {r["instance_id"]: r for r in results}

    for idx, iid in enumerate(cands):
        if iid in by_id and by_id[iid].get("done"):
            print(f"{iid} cached", file=sys.stderr); continue
        r = rows[iid]; files = p0.parse_patch(r.get("patch") or "")
        gold_files = {f for f in files if f.endswith(".py")}
        gold_lines = {f: files[f]["region"] for f in gold_files}
        total_gold = sum(len(v) for v in gold_lines.values())
        issue = (r.get("problem_statement") or "")[:5000]
        ftp = r.get("FAIL_TO_PASS")
        if isinstance(ftp, str):
            try: ftp = json.loads(ftp)
            except: ftp = []
        rec = {"instance_id": iid, "repo": r["repo"], "gold_files": sorted(gold_files),
               "n_gold_files": len(gold_files), "total_gold_lines": total_gold}

        # ---- S1a: static file localization ----
        try:
            tree = p1.fetch_tree(r["repo"], r["base_commit"])
            fp = p1.FILE_PROMPT.format(issue=issue, nfiles=len(tree["paths"]), filelist="\n".join(tree["paths"]))
            static_files = p1.parse_str_list(_llm(model, fp))[:args.topk]
        except Exception as e:
            rec["error"] = "static/tree: " + repr(e)[:120]; by_id[iid] = rec
            results = list(by_id.values()); out.write_text(json.dumps({"results": results}, indent=2)); continue
        rec["n_repo_pyfiles"] = len(tree["paths"])

        # ---- S1b: called-coverage narrowing (Docker, one run) ----
        called_files = set()
        cont = "hla_" + re.sub(r'[^a-z0-9_]', '_', iid.lower()); tag = egl.img_tag(iid); container_up = False
        if not args.no_exec:
            try:
                if egl.docker("image", "inspect", tag).returncode != 0:
                    if egl.docker("pull", tag, timeout=1800).returncode != 0:
                        rec["exec_error"] = "pull"
                if "exec_error" not in rec:
                    egl.docker("rm", "-f", cont); egl.docker("run", "-d", "--name", cont, tag, "sleep", "infinity"); container_up = True
                    ptxt = (r.get("test_patch") or "").replace("\r\n", "\n")
                    if not ptxt.endswith("\n"): ptxt += "\n"
                    tp = os.path.join(tempfile.gettempdir(), f"hla_{iid.replace('/','_')}.patch")
                    open(tp, "wb").write(ptxt.encode()); egl.docker("cp", tp, f"{cont}:/tmp/test.patch"); os.unlink(tp)
                    npy = os.path.join(tempfile.gettempdir(), "hla_narrow.py")
                    open(npy, "wb").write(p7.NARROW_PY.encode()); egl.docker("cp", npy, f"{cont}:/tmp/narrow.py"); os.unlink(npy)
                    run_sh = p7.RUN_SH.replace("%TESTS%", " ".join(f"'{t}'" for t in ftp[:6])).replace("%MIRROR%", MIRROR)
                    egl.docker("exec", cont, "bash", "-lc", run_sh, timeout=1800)
                    cjf = egl.docker("exec", cont, "cat", "/tmp/called.json")
                    if cjf.returncode == 0 and cjf.stdout.strip():
                        for fpath in json.loads(cjf.stdout):
                            nf = p7.norm(fpath)
                            if p7.is_repo_src(nf): called_files.add(nf)
            except Exception as e:
                rec["exec_error"] = repr(e)[:150]

        # ---- S1c: graph NAVIGATION — additively expand static picks with import neighbors ----
        # fetch sources for static picks + coverage files (needed for neighbors + line-loc/loop)
        file_srcs = {}
        for f in dict.fromkeys(static_files + sorted(called_files)):
            if f not in tree["paths"]: continue
            try:
                s = p0.fetch_file(r["repo"], r["base_commit"], f)
                if 0 < len(s.splitlines()) <= 3000: file_srcs[f] = s
            except Exception: pass
        neigh = import_neighbors(file_srcs, tree["paths"])
        for f in neigh:                                  # fetch neighbor sources too
            if f not in file_srcs:
                try:
                    s = p0.fetch_file(r["repo"], r["base_commit"], f)
                    if 0 < len(s.splitlines()) <= 3000: file_srcs[f] = s
                except Exception: pass
        # graph-augmented candidate set = static (strong LLM ranking) + coverage + import neighbors
        graph_files = list(dict.fromkeys(static_files + sorted(called_files) + neigh))
        def fr(s): return round(len(set(s) & gold_files) / len(gold_files), 3)
        rec.update({"n_static": len(static_files), "n_called": len(called_files), "n_neigh": len(neigh),
                    "fr_static": fr(static_files),
                    "fr_static_called": fr(set(static_files) | called_files),
                    "fr_graph": fr(graph_files),
                    "all_found_static": int(fr(static_files) >= 0.999),
                    "all_found_graph": int(fr(graph_files) >= 0.999),
                    "recovered_by_graph": sorted((gold_files & set(neigh)) - set(static_files) - called_files),
                    "recovered_by_called": sorted((gold_files & called_files) - set(static_files))})

        # ---- S2: line localization within FOUND gold files (static vs graph, SAME flat parser) ----
        def line_loc(found, use_graph):
            hit = 0; ranked_global = []
            for f in found:
                if f not in file_srcs: continue
                src = file_srcs[f]; numbered = "\n".join(f"{i+1}: {ln}" for i, ln in enumerate(src.splitlines()))
                try:
                    if use_graph:
                        g = cg.CodeGraph(src, f); gtxt, _ = _graph_block(g, issue)
                        rk = parse_ranked(_llm(model, LINE_PROMPT_G.format(issue=issue, path=f, numbered=numbered, graph=gtxt)))
                    else:
                        rk = parse_ranked(_llm(model, RANK_PROMPT.format(issue=issue, path=f, numbered=numbered)))
                except Exception: rk = []
                hit += len(set(rk) & gold_lines[f]); ranked_global += [(f, ln) for ln in rk]
                time.sleep(0.2)
            return (round(hit / total_gold, 3) if total_gold else 0.0), ranked_global
        found_static = [f for f in static_files if f in gold_files]
        found_graph = [f for f in graph_files if f in gold_files]
        rec["line_recall_static"], rs_global = line_loc(found_static, False)
        rec["line_recall_graph"], rg_global = line_loc(found_graph, True)
        goldflat = set(gold_lines_flat(gold_lines))
        rec.update({f"line_R@{k}_static": hit_at_k(rs_global, goldflat, k) for k in KS})
        rec.update({f"line_R@{k}": hit_at_k(rg_global, goldflat, k) for k in KS})

        # ---- S3: multi-file exec-feedback loop ----
        if not args.no_loop and not args.no_exec and container_up:
            loop_files = [f for f in graph_files if f in file_srcs and len(file_srcs[f].splitlines()) <= args.max_file_lines][:args.loop_files]
            # ensure gold files we DID find are editable in the loop
            for f in found_graph:
                if f in file_srcs and f not in loop_files and len(file_srcs[f].splitlines()) <= args.max_file_lines:
                    loop_files.append(f)
            srcs0 = {f: file_srcs[f] for f in loop_files}
            try:
                rec["loop"] = run_mf_loop(model, issue, srcs0, gold_lines, gold_files, total_gold,
                                          cont, ftp, args.rounds, tree, r)
            except Exception as e:
                rec["loop_error"] = repr(e)[:200]

        if container_up:
            egl.docker("rm", "-f", cont)
            if not args.keep_images: egl.docker("rmi", tag)
        rec["done"] = True; by_id[iid] = rec; results = list(by_id.values())
        out.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")
        lp = rec.get("loop", {})
        print(f"[{idx+1}/{len(cands)}] {iid:30s} fr_static={rec['fr_static']} fr_graph={rec['fr_graph']} "
              f"lr_static={rec['line_recall_static']} lr_graph={rec['line_recall_graph']} "
              f"loop_fr={lp.get('file_recall')} loop_lr={lp.get('line_recall')}", file=sys.stderr); sys.stderr.flush()

    summarize(results, out)

def gold_lines_flat(gl):
    return {(f, ln) for f, s in gl.items() for ln in s}

def _graph_block(g, issue, failure=""):
    from hybrid_loop import graph_block
    return graph_block(g, issue, failure)

def run_mf_loop(model, issue, srcs0, gold_lines, gold_files, total_gold, cont, ftp, rounds, tree, row):
    """Multi-file static->exec->feedback loop. srcs0={path:original}. Traceback
    re-seeds the candidate set with newly named repo files. Returns loop metrics."""
    run_sh = (r'''source /opt/miniconda3/etc/profile.d/conda.sh 2>/dev/null || true
conda activate testbed 2>/dev/null || true
cd /testbed
timeout 240 python -m pytest -p no:cacheprovider --no-header -o addopts="" --tb=short -q %TESTS% > /tmp/po.out 2>&1
echo "RC=$?"
tail -c 4000 /tmp/po.out''').replace("%TESTS%", " ".join(f"'{t}'" for t in ftp[:6]))
    srcs = dict(srcs0); located = {}; failures = []; per_round = []; solved = False
    for rd in range(rounds):
        graph_cands = {}
        for f, s in srcs.items():
            g = cg.CodeGraph(s, f)
            graph_cands[f] = g.rank_suspect_lines(issue, failures[-1] if failures else "", topn=12)
        files_block = "\n\n".join(numbered_block(f, srcs0[f], graph_cands) for f in srcs)
        failblock = ""
        if failures:
            fb = "\n\n".join(f"[attempt {j+1}]\n{x[:1400]}" for j, x in enumerate(failures))
            failblock = f"\n## Previous failed attempts (test still failing):\n{fb}\n"
        try:
            resp = _llm(model, REPAIR_MF.format(issue=issue, failblock=failblock, files=files_block))
        except Exception as e:
            per_round.append({"round": rd, "edited": 0, "passed": False, "llm_error": repr(e)[:80]}); continue
        edits = parse_mf_edits(resp)
        if not edits:
            per_round.append({"round": rd, "edited": 0, "passed": False, "no_edits": True})
            failures.append("(no valid path-tagged SEARCH/REPLACE blocks; follow the format)"); continue
        newsrcs, edited = apply_mf_edits(srcs0, edits)
        for f, lns in edited.items():
            located.setdefault(f, set()).update(lns)
        # apply edited files in container
        for f in edited:
            fp = os.path.join(tempfile.gettempdir(), f"hla_e_{re.sub(r'[^a-z0-9]','_',cont)}.src")
            open(fp, "w", encoding="utf-8").write(newsrcs[f]); egl.docker("cp", fp, f"{cont}:/testbed/{f}"); os.unlink(fp)
        ex = egl.docker("exec", cont, "bash", "-lc", run_sh, timeout=360)
        m = re.search(r"RC=(\d+)", ex.stdout); rc = int(m.group(1)) if m else 1
        failure = ex.stdout.split("\n", 1)[1] if "\n" in ex.stdout else ex.stdout
        nloc = sum(len(v) for v in located.values())
        per_round.append({"round": rd, "edited_files": len(edited), "edited": nloc, "passed": rc == 0})
        if rc == 0: solved = True; break
        failures.append(failure)
        # traceback re-seeds: pull newly named repo files into the editable set
        for mm in re.findall(r"([A-Za-z0-9_./-]+\.py):\d+", failure):
            nf = p7.norm(mm)
            if p7.is_repo_src(nf) and nf in tree["paths"] and nf not in srcs and len(srcs) < 6:
                try:
                    s = p0.fetch_file(row["repo"], row["base_commit"], nf)
                    if 0 < len(s.splitlines()) <= 800: srcs[nf] = s; srcs0[nf] = s
                except Exception: pass
    # metrics
    found = {f for f in located if located[f]}
    file_recall = round(len(found & gold_files) / len(gold_files), 3) if gold_files else 0.0
    line_hit = sum(len(located.get(f, set()) & gold_lines[f]) for f in gold_files)
    line_recall = round(line_hit / total_gold, 3) if total_gold else 0.0
    # global ranked (f,line) by graph suspiciousness for Line Recall@k
    ranked = []
    for f in srcs0:
        g = cg.CodeGraph(srcs0[f], f); order = g.rank_suspect_lines(issue, "\n".join(failures), topn=400)
        pos = {ln: i for i, ln in enumerate(order)}
        for ln in sorted(located.get(f, set()), key=lambda x: pos.get(x, 10 ** 6)):
            ranked.append((f, ln))
    goldflat = gold_lines_flat(gold_lines)
    return {"file_recall": file_recall, "line_recall": line_recall, "solved": solved,
            "n_located_lines": sum(len(v) for v in located.values()),
            "n_located_files": len(found), "edited_files": sorted(found),
            "rounds_run": len(per_round), "per_round": per_round,
            **{f"line_R@{k}": hit_at_k(ranked, goldflat, k) for k in KS}}

def summarize(results, out):
    import statistics as st
    ok = [r for r in results if r.get("fr_static") is not None and "error" not in r]
    if not ok:
        print("no results", file=sys.stderr); return
    def mean(k, src=None):
        vals = [(src(r) if src else r.get(k)) for r in ok]
        vals = [v for v in vals if v is not None]
        return round(st.mean(vals), 3) if vals else None
    loops = [r["loop"] for r in ok if "loop" in r]
    def Rk(key): return round(100 * st.mean(r.get(key, 0) for r in ok), 1)
    summary = {"n": len(ok),
               "fr_static": mean("fr_static"), "fr_static_called": mean("fr_static_called"),
               "fr_graph(+neigh)": mean("fr_graph"),
               "all_found_static": sum(r["all_found_static"] for r in ok),
               "all_found_graph": sum(r["all_found_graph"] for r in ok),
               "line_recall_static": mean("line_recall_static"),
               "line_recall_graph": mean("line_recall_graph"),
               "line_R@k_static_loc": {k: Rk(f"line_R@{k}_static") for k in KS},
               "line_R@k_graph_loc": {k: Rk(f"line_R@{k}") for k in KS},
               "instances_graph_recovered_file": sum(1 for r in ok if r.get("recovered_by_graph")),
               "instances_cov_recovered_file": sum(1 for r in ok if r.get("recovered_by_called"))}
    if loops:
        summary["loop"] = {"n": len(loops),
                           "file_recall": round(st.mean(l["file_recall"] for l in loops), 3),
                           "line_recall": round(st.mean(l["line_recall"] for l in loops), 3),
                           "solved_rate": round(st.mean(1 if l["solved"] else 0 for l in loops), 3),
                           **{f"line_R@{k}": round(100 * st.mean(l[f"line_R@{k}"] for l in loops), 1) for k in KS}}
    d = json.loads(out.read_text()); d["summary"] = summary; out.write_text(json.dumps(d, indent=2), encoding="utf-8")
    print("\n==== SUMMARY ====\n" + json.dumps(summary, indent=2), file=sys.stderr)

if __name__ == "__main__":
    main()
