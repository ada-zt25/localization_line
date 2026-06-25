#!/usr/bin/env python3
"""hybrid_loop (formerly P8) — the static+dynamic execution-feedback localization
method, now with an ARISE-style code-graph augmenting BOTH links.

Pipeline: static LLM proposes SEARCH/REPLACE edits (edit = localization) -> run
FAIL_TO_PASS in the official SWE-bench container -> feed the new failure back ->
re-localize -> K rounds. Localization = union of edited lines over rounds.

This file runs a 4-variant ABLATION per instance (single-file, file-given, the same
seed-3 set as the old P8 so numbers are apples-to-apples):

  A0 static_plain : LLM ranks suspect lines from issue + numbered file        (no exec)
  A1 static_graph : + code_graph skeleton + def-use slice candidates in prompt (no exec)
  B0 loop_plain   : the original P8 exec-feedback loop                          (Docker)
  B1 loop_graph   : loop whose prompts carry the graph skeleton + per-round,
                    traceback-RESEEDED def-use slice candidates; the located union
                    is RANKED by graph suspiciousness (the confidence ordering the
                    old P8 union lacked -> the fix for its Recall@1 loss).        (Docker)

Why the graph: ARISE (arXiv:2605.03117) shows statement-level def-use slicing is the
active ingredient for line-level recall. Here the graph is a TOOL the localizer reads
(skeleton + candidate lines), not a standalone ranker. See code_graph.py.

    OPENAI_BASE_URL=https://api.siliconflow.com/v1 MODEL=deepseek-ai/DeepSeek-V3 \
        python hybrid_loop.py --sample 15 --rounds 5
        python hybrid_loop.py --sample 15 --no-loop     # A0/A1 only (no Docker, fast)
"""
from __future__ import annotations
import argparse, difflib, json, os, re, ssl, sys, tempfile, time, urllib.request
from pathlib import Path
import p0_line_recall as p0
import egl_makeorbreak as egl
import code_graph as cg

HERE = Path(__file__).resolve().parent
MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple"
CTX = ssl.create_default_context()
KS = (1, 5, 10)

def _llm(model, prompt, timeout=300, retries=3):
    """Bounded but resilient OpenAI-compatible call (full-file/edit outputs can drop
    the SiliconFlow connection mid-stream -> retry generously)."""
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    key = p0._openai_key()
    payload = {"model": model, "temperature": 0, "messages": [{"role": "user", "content": prompt}]}
    if any(x in model.lower() for x in ("v4", "glm")):   # reasoning-by-default -> disable (too slow for batch)
        payload["thinking"] = {"type": "disabled"}
    body = json.dumps(payload).encode()
    for a in range(retries):
        try:
            req = urllib.request.Request(base + "/chat/completions", data=body,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
            return json.loads(urllib.request.urlopen(req, timeout=timeout, context=CTX).read())["choices"][0]["message"]["content"]
        except Exception:
            if a == retries - 1:
                raise
            time.sleep(min(30, 5 * (a + 1)))

PYTEST = {"astropy/astropy","scikit-learn/scikit-learn","pydata/xarray",
          "psf/requests","matplotlib/matplotlib","pallets/flask"}

SETUP_SH = r'''
source /opt/miniconda3/etc/profile.d/conda.sh 2>/dev/null || true
conda activate testbed 2>/dev/null || true
cd /testbed
python -c "import pytest" 2>/dev/null || timeout 200 python -m pip -q install pytest 2>/dev/null || timeout 200 python -m pip -q install -i %MIRROR% pytest 2>/dev/null || true
( git apply /tmp/test.patch 2>/dev/null && echo APPLY_OK ) || ( git apply --3way /tmp/test.patch 2>/dev/null && echo APPLY_OK ) || echo APPLY_FAILED
'''
RUN_SH = r'''
source /opt/miniconda3/etc/profile.d/conda.sh 2>/dev/null || true
conda activate testbed 2>/dev/null || true
cd /testbed
timeout 240 python -m pytest -p no:cacheprovider --no-header -o addopts="" --tb=short -q %TESTS% > /tmp/po.out 2>&1
echo "RC=$?"
tail -c 3500 /tmp/po.out
'''

EDIT_FMT = """Output one or more EDIT BLOCKS, each in EXACTLY this format:
<<<<<<< SEARCH
(exact consecutive lines copied verbatim from the file above, WITHOUT the "N: " line-number prefix)
=======
(the replacement lines)
>>>>>>> REPLACE
The SEARCH text must match the file byte-for-byte. Output ONLY edit blocks, no commentary."""

REPAIR0 = """You are fixing a GitHub issue by editing ONE Python file.

## Issue
{issue}

## File: {path}
{numbered}

## Task
Produce the minimal edit(s) that fix the issue. """ + EDIT_FMT

REPAIR_N = """You are fixing a GitHub issue by editing ONE Python file. Your previous fix attempts did NOT make the test pass.

## Issue
{issue}

## Previous failed attempts (test still failing):
{failures}

## File (with line numbers):
{numbered}

## Task
The fix likely needs DIFFERENT or ADDITIONAL locations than you tried. Reconsider using the failures above.
Produce the minimal edit(s). """ + EDIT_FMT

# ---- graph-augmented variants (ARISE-style structural context block) --------
GRAPH_CTX = """## Code structure (call graph; def = function, [L..] = line span, -> calls)
{skeleton}

## Data-flow candidate lines (a def-use slice from the issue{tb}) — ADVISORY hints only,
## possibly incomplete or wrong. Rely on your own reading of the issue and code; use these
## only as a checklist so you don't miss structurally/data-flow-connected locations:
{cands}
"""
REPAIR0_G = """You are fixing a GitHub issue by editing ONE Python file.

## Issue
{issue}

{graph}
## File: {path}
{numbered}

## Task
Use the structure above to find ALL decisive locations, then produce the minimal edit(s). """ + EDIT_FMT

REPAIR_N_G = """You are fixing a GitHub issue by editing ONE Python file. Your previous fix attempts did NOT make the test pass.

## Issue
{issue}

## Previous failed attempts (test still failing):
{failures}

{graph}
## File (with line numbers):
{numbered}

## Task
The fix likely needs DIFFERENT or ADDITIONAL locations than you tried. The candidate
lines above were re-derived from the LATEST failure's traceback. Reconsider with them.
Produce the minimal edit(s). """ + EDIT_FMT

RANK_PROMPT = """You are localizing the exact code lines that must be edited to resolve a GitHub issue.

## Issue
{issue}

## File: {path}
{numbered}

## Task
List the line numbers MOST LIKELY to need editing, RANKED from most likely to least likely.
Output ONLY a JSON array of line numbers (most-likely first), up to 15, e.g. [88, 89, 42]. JSON only."""

RANK_PROMPT_G = """You are localizing the exact code lines that must be edited to resolve a GitHub issue.

## Issue
{issue}

{graph}
## File: {path}
{numbered}

## Task
Using the code structure and candidate lines above, list the line numbers MOST LIKELY to
need editing, RANKED from most likely to least likely.
Output ONLY a JSON array of line numbers (most-likely first), up to 15, e.g. [88, 89, 42]. JSON only."""

# ------------------------------ parsing --------------------------------------

def parse_edits(text):
    return [(s, r) for s, r in re.findall(
        r"<<<<<<< SEARCH\s*\n(.*?)\n=======\s*\n(.*?)\n>>>>>>> REPLACE", text, re.S)]

def _deprefix(block):
    return "\n".join(re.sub(r'^\s*\d+:\s?', '', ln) for ln in block.split("\n"))

def apply_edits(orig, edits):
    new = orig; edited = set()
    for search, replace in edits:
        if not search.strip():
            continue
        for s, rep in ((search, replace), (_deprefix(search), _deprefix(replace))):
            if s in orig:
                idx = orig.find(s)
                start = orig.count("\n", 0, idx) + 1
                end = start + s.count("\n")
                edited.update(range(start, end + 1))
                new = new.replace(s, rep, 1)
                break
    return new, edited

def parse_ranked(text):
    m = re.search(r"\[[\s\d,]*\]", text)
    out = []
    if m:
        try:
            for v in json.loads(m.group(0)):
                if isinstance(v, int) and v not in out: out.append(v)
        except Exception: pass
    if not out:
        for v in re.findall(r"\d+", text):
            iv = int(v)
            if iv not in out: out.append(iv)
    return out

def hit_at_k(ranked, gold, k):
    return 1 if (set(ranked[:k]) & gold) else 0

def metrics_ranked(ranked, gold):
    return {"ranked": ranked, "n_pred": len(ranked),
            "recall_frac": round(len(set(ranked) & gold) / len(gold), 3) if gold else 0.0,
            **{f"hit@{k}": hit_at_k(ranked, gold, k) for k in KS}}

# ------------------------------ graph block ----------------------------------

def graph_block(g, issue, failure=""):
    """Build the GRAPH_CTX text (skeleton + def-use-slice candidate lines, the
    candidates RESEEDED by the latest traceback when one is supplied)."""
    if not g.ok:
        return "", []
    cands = g.rank_suspect_lines(issue, failure, topn=15)
    cand_txt = ", ".join(f"L{c}" for c in cands) if cands else "(none derived)"
    tb = " + the latest test traceback" if failure else ""
    return GRAPH_CTX.format(skeleton=g.skeleton(max_funcs=40), cands=cand_txt, tb=tb), cands

# ------------------------------ the loop -------------------------------------

def run_loop(model, issue, orig, gold, path, cont, run_sh, rounds, graph=None):
    """One static->exec->feedback loop. graph=None -> loop_plain; graph set ->
    loop_graph (graph-augmented prompts + traceback-reseeded candidates + the union
    ranked by graph suspiciousness). Returns the per-variant record. Assumes the
    ORIGINAL file is already in the container at /testbed/{path}."""
    numbered = "\n".join(f"{i+1}: {ln}" for i, ln in enumerate(orig.splitlines()))
    failures = []; located = set(); per_round = []; round_lines = []; solved = False
    for rd in range(rounds):
        if graph is not None:
            gtxt, _ = graph_block(graph, issue, failures[-1] if failures else "")
            if rd == 0 or not failures:
                prompt = REPAIR0_G.format(issue=issue, path=path, numbered=numbered, graph=gtxt)
            else:
                fb = "\n\n".join(f"[attempt {j+1}]\n{f[:1500]}" for j, f in enumerate(failures))
                prompt = REPAIR_N_G.format(issue=issue, failures=fb, numbered=numbered, graph=gtxt)
        else:
            if rd == 0 or not failures:
                prompt = REPAIR0.format(issue=issue, path=path, numbered=numbered)
            else:
                fb = "\n\n".join(f"[attempt {j+1}]\n{f[:1500]}" for j, f in enumerate(failures))
                prompt = REPAIR_N.format(issue=issue, failures=fb, numbered=numbered)
        try:
            resp = _llm(model, prompt)
        except Exception as e:
            per_round.append({"round": rd, "edited": 0, "recall": 0.0, "passed": False, "llm_error": repr(e)[:80]}); continue
        edits = parse_edits(resp)
        if not edits:
            per_round.append({"round": rd, "edited": 0, "recall": 0.0, "passed": False, "no_edits": True})
            failures.append("(your previous output had no valid SEARCH/REPLACE blocks; follow the format exactly)"); continue
        Fi, Ei = apply_edits(orig, edits); located |= Ei; round_lines.append(sorted(Ei))
        fpath = os.path.join(tempfile.gettempdir(), f"hl_{re.sub(r'[^a-z0-9]','_',cont)}.src")
        open(fpath, "w", encoding="utf-8").write(Fi); egl.docker("cp", fpath, f"{cont}:/testbed/{path}"); os.unlink(fpath)
        ex = egl.docker("exec", cont, "bash", "-lc", run_sh, timeout=360)
        m = re.search(r"RC=(\d+)", ex.stdout); rc = int(m.group(1)) if m else 1
        failure = ex.stdout.split("\n", 1)[1] if "\n" in ex.stdout else ex.stdout
        er = round(len(Ei & gold) / len(gold), 3) if gold else 0.0
        per_round.append({"round": rd, "edited": len(Ei), "recall": er, "passed": rc == 0})
        if rc == 0: solved = True; break
        failures.append(failure)
    # ranked union: graph variant -> by graph suspiciousness; else discovery order
    if graph is not None and graph.ok:
        allfail = "\n".join(failures)
        gorder = graph.rank_suspect_lines(issue, allfail, topn=400)
        pos = {ln: i for i, ln in enumerate(gorder)}
        ranked = sorted(located, key=lambda ln: (pos.get(ln, 10 ** 6),))
        # append any discovery-order remainder not scored by the graph
    else:
        ranked, seen = [], set()
        for rl in round_lines:
            for ln in rl:
                if ln not in seen: seen.add(ln); ranked.append(ln)
    _real = [p for p in per_round if p.get("edited", 0) > 0]
    rec = {"recall_round0": _real[0]["recall"] if _real else 0.0,
           "recall_loop": round(len(located & gold) / len(gold), 3) if gold else 0.0,
           "prec_loop": round(len(located & gold) / len(located), 3) if located else 0.0,
           "n_located": len(located), "solved": solved, "rounds_run": len(per_round),
           "located_ranked": ranked, "per_round_lines": round_lines, "per_round": per_round,
           **{f"hit@{k}": hit_at_k(ranked, gold, k) for k in KS}}
    return rec

# -------------------------------- driver -------------------------------------

def select_instances(max_lines=400, n=15):
    rows = {r["instance_id"]: r for r in p0.load_rows(500)}
    import random
    cand = []
    for iid, r in rows.items():
        if r["repo"] not in PYTEST: continue
        files = p0.parse_patch(r.get("patch") or "")
        py = [f for f in files if f.endswith(".py")]
        if len(files) == 1 and len(py) == 1 and files[py[0]]["hunks"] and r.get("FAIL_TO_PASS"):
            cand.append(iid)
    random.Random(3).shuffle(cand)
    sel = []
    for iid in cand:
        if len(sel) >= n: break
        r = rows[iid]; files = p0.parse_patch(r.get("patch") or "")
        path = [f for f in files if f.endswith(".py")][0]
        try: src = p0.fetch_file(r["repo"], r["base_commit"], path)
        except Exception: continue
        if not (0 < len(src.splitlines()) <= max_lines): continue
        sel.append((iid, r, path, files[path], src))
    return sel

def cp_original(orig, cont, path):
    fp = os.path.join(tempfile.gettempdir(), f"hl_orig_{re.sub(r'[^a-z0-9]','_',cont)}.src")
    open(fp, "w", encoding="utf-8").write(orig); egl.docker("cp", fp, f"{cont}:/testbed/{path}"); os.unlink(fp)

def summarize(results, variants):
    import statistics as st
    ok = [r for r in results if any(v in r for v in variants)]
    summary = {"n": len(ok)}
    for v in variants:
        rs = [r[v] for r in ok if v in r]
        if not rs: continue
        s = {"n": len(rs),
             "recall_frac": round(st.mean(r.get("recall_loop", r.get("recall_frac", 0)) for r in rs), 3),
             **{f"R@{k}": round(100 * st.mean(r[f"hit@{k}"] for r in rs), 1) for k in KS}}
        if "recall_round0" in rs[0]:
            s["recall_round0"] = round(st.mean(r["recall_round0"] for r in rs), 3)
            s["delta_recall"] = round(s["recall_frac"] - s["recall_round0"], 3)
            s["solved_rate"] = round(st.mean(1 if r.get("solved") else 0 for r in rs), 3)
            s["mean_located"] = round(st.mean(r["n_located"] for r in rs), 1)
        summary[v] = s
    return summary

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=15)
    ap.add_argument("--rounds", type=int, default=5)
    ap.add_argument("--max-lines", type=int, default=400)
    ap.add_argument("--no-loop", action="store_true", help="A0/A1 only (no Docker)")
    ap.add_argument("--keep-images", action="store_true", help="don't rmi after each instance")
    ap.add_argument("--out", default=str(HERE / "hybrid_loop.json"))
    args = ap.parse_args()
    model = os.environ.get("MODEL", "deepseek-ai/DeepSeek-V3")
    variants = ["static_plain", "static_graph"] + ([] if args.no_loop else ["loop_plain", "loop_graph"])

    sel = select_instances(args.max_lines, args.sample)
    print(f"[hybrid_loop] {len(sel)} instances; variants={variants}", file=sys.stderr)
    out = Path(args.out)
    results = json.loads(out.read_text())["results"] if out.exists() else []
    by_id = {r["instance_id"]: r for r in results}

    for iid, r, path, goldinfo, orig in sel:
        rec = by_id.get(iid) or {"instance_id": iid, "repo": r["repo"], "path": path}
        if all(v in rec for v in variants):
            print(f"{iid} cached", file=sys.stderr); continue
        gold = goldinfo["region"]
        rec.update({"n_gold": len(gold), "file_lines": len(orig.splitlines()),
                    "gold_lines": sorted(gold), "gold_del": sorted(goldinfo.get("deleted", set()))})
        issue = (r.get("problem_statement") or "")[:5000]
        numbered = "\n".join(f"{i+1}: {ln}" for i, ln in enumerate(orig.splitlines()))
        g = cg.CodeGraph(orig, path)
        # ---- A0 static_plain / A1 static_graph (no Docker) ----
        try:
            if "static_plain" not in rec:
                rk = parse_ranked(_llm(model, RANK_PROMPT.format(issue=issue, path=path, numbered=numbered)))
                rec["static_plain"] = metrics_ranked(rk, gold)
            if "static_graph" not in rec:
                gtxt, _ = graph_block(g, issue)
                rk = parse_ranked(_llm(model, RANK_PROMPT_G.format(issue=issue, path=path, numbered=numbered, graph=gtxt)))
                rec["static_graph"] = metrics_ranked(rk, gold)
        except Exception as e:
            rec["static_error"] = repr(e)[:120]
        # ---- B0 loop_plain / B1 loop_graph (Docker) ----
        if not args.no_loop and not all(v in rec for v in ("loop_plain", "loop_graph")):
            ftp = r.get("FAIL_TO_PASS")
            if isinstance(ftp, str):
                try: ftp = json.loads(ftp)
                except: ftp = []
            tag = egl.img_tag(iid); cont = "hl_" + re.sub(r'[^a-z0-9_]', '_', iid.lower())
            try:
                if egl.docker("image", "inspect", tag).returncode != 0:
                    if egl.docker("pull", tag, timeout=1800).returncode != 0:
                        rec["loop_error"] = "pull"; by_id[iid] = rec; results = list(by_id.values())
                        out.write_text(json.dumps({"results": results}, indent=2)); continue
                egl.docker("rm", "-f", cont); egl.docker("run", "-d", "--name", cont, tag, "sleep", "infinity")
                try:
                    ptxt = (r.get("test_patch") or "").replace("\r\n", "\n")
                    if not ptxt.endswith("\n"): ptxt += "\n"
                    tp = os.path.join(tempfile.gettempdir(), f"hl_{iid.replace('/','_')}.patch")
                    open(tp, "wb").write(ptxt.encode()); egl.docker("cp", tp, f"{cont}:/tmp/test.patch"); os.unlink(tp)
                    egl.docker("exec", cont, "bash", "-lc", SETUP_SH.replace("%MIRROR%", MIRROR), timeout=400)
                    run_sh = RUN_SH.replace("%TESTS%", " ".join(f"'{t}'" for t in ftp[:6]))
                    if "loop_plain" not in rec:
                        cp_original(orig, cont, path)
                        rec["loop_plain"] = run_loop(model, issue, orig, gold, path, cont, run_sh, args.rounds, graph=None)
                    if "loop_graph" not in rec:
                        cp_original(orig, cont, path)
                        rec["loop_graph"] = run_loop(model, issue, orig, gold, path, cont, run_sh, args.rounds, graph=g)
                finally:
                    egl.docker("rm", "-f", cont)
                    if not args.keep_images: egl.docker("rmi", tag)
            except Exception as e:
                rec["loop_error"] = repr(e)[:200]
        by_id[iid] = rec; results = list(by_id.values())
        out.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")
        msg = " ".join(f"{v}:R@1={rec[v].get('hit@1')},frac={rec[v].get('recall_loop', rec[v].get('recall_frac'))}"
                       for v in variants if v in rec)
        print(f"{iid:30s} {msg}", file=sys.stderr); sys.stderr.flush()

    summary = summarize(results, variants)
    d = json.loads(out.read_text()); d["summary"] = summary; out.write_text(json.dumps(d, indent=2), encoding="utf-8")
    print("\n==== SUMMARY ====\n" + json.dumps(summary, indent=2), file=sys.stderr)

if __name__ == "__main__":
    main()
