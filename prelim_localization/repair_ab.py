#!/usr/bin/env python3
"""repair_ab — END-TO-END REPAIR-RATE A/B: does SPINE line-localization convert into a HIGHER
SWE-bench resolve rate than the baseline localization?

Causal isolation: for each instance we run TWO repair arms that are identical except for WHICH
lines the repair model is shown. Each arm conditions the repair on a WINDOW (+-W lines) around that
arm's top-K localized lines, then generates SEARCH/REPLACE edits, applies them, and runs FAIL_TO_PASS
in the official SWE-bench container. If SPINE puts the buggy line in-window more often, its arm resolves
more. Same repair model, same file, same container, same tests — the ONLY difference is the localization.

  arm 'vote'  : window around vote_only top-K   (coverage-free self-consistency baseline)
  arm 'm5'    : window around ours_m5 top-K      (SPINE assertion-reranked)
  (optionally arm 'm5vb' : ours_m5_votebase, the coverage-neutral SPINE, if present)

Localization is READ from a prior egl_e2e run's per-instance `ranks` dump (needs that run to have used
--dump-ranks). Reuses hybrid_loop's edit/apply + egl_makeorbreak's docker driver — no reinvention.

Usage:
  SWEBENCH_DATASET=lite OPENAI_BASE_URL=... MODEL=<repair-model> \
    python3 repair_ab.py --loc-run runs/spine_behav132_dsv32.json --arms vote m5 m5vb \
      --k 3 --window 30 --out runs/repair_ab_dsv32.json [--smoke 3]
"""
import argparse, json, os, re, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import p0_line_recall as p0
import egl_makeorbreak as egl
import code_graph as cg
from hybrid_loop import _llm, apply_edits, parse_edits, EDIT_FMT, SETUP_SH, RUN_SH, MIRROR
import spine_paired_stats as sp

REPAIR_WIN = """You are fixing a GitHub issue by editing ONE Python file. Below is the SUSPECTED-BUGGY
region of {path} (a fault localizer flagged these lines as most likely to contain the bug). Edit this
code so the failing test passes and the issue is resolved.

## Issue
{issue}

## Failing test (what must pass)
{tests}

## Suspected region of {path} (line-numbered; edit within this region)
{window}

{editfmt}"""


def windowed(orig_lines, center_lines, W):
    """Numbered text of the union of [ln-W, ln+W] around each center line (real line numbers)."""
    keep = set()
    for ln in center_lines:
        keep.update(range(max(1, ln - W), min(len(orig_lines), ln + W) + 1))
    return "\n".join(f"{i}: {orig_lines[i-1]}" for i in sorted(keep)), keep


def ctx_lines(orig_lines, center_lines, g, W, cap):
    """Localization-conditioned context = union of the ENCLOSING FUNCTION of each center line
    (via code_graph line_func/funcs); fall back to +-W window for module-level lines or when the
    enclosing function is bigger than `cap`. Returns (numbered_text, kept_lineset)."""
    keep = set()
    for ln in center_lines:
        fi = g.line_func.get(ln) if (g and g.ok) else None
        if fi is not None:
            f = g.funcs[fi]
            if f["end"] - f["start"] + 1 <= cap:
                keep.update(range(f["start"], f["end"] + 1)); continue
        keep.update(range(max(1, ln - W), min(len(orig_lines), ln + W) + 1))
    return "\n".join(f"{i}: {orig_lines[i-1]}" for i in sorted(keep)), keep


REPAIR_CTX = """You are fixing a GitHub issue by editing ONE Python file. Below is the SUSPECTED-BUGGY
code of {path} (a fault localizer flagged the enclosing function(s) most likely to contain the bug).
Edit it so the failing test passes and the issue is resolved.

## Issue
{issue}

## Failing test (must pass)
{tests}
{feedback}
## Code to edit ({path}, line-numbered)
{ctx}

{editfmt}"""


def repair_arm_loop(model, issue, orig, path, top_lines, gold, ftp_names, cont, run_sh, rounds, g, W, cap):
    """Feedback-loop repair conditioned on the localized enclosing-function context. Up to `rounds`
    attempts: propose edits -> apply -> run FAIL_TO_PASS -> on fail feed the error back -> retry.
    resolved = any round passes. Same machinery as hybrid_loop.run_loop but the model sees ONLY the
    localized function(s), so localization gates repair."""
    olines = orig.splitlines()
    ctx, keep = ctx_lines(olines, top_lines, g, W, cap)
    loc_has_gold = bool(keep & gold)
    failures = []
    for rd in range(rounds):
        fb = ("\n## Your previous attempt FAILED — fix based on this test output:\n"
              + "\n\n".join(f[:1200] for f in failures[-2:]) + "\n") if failures else ""
        prompt = REPAIR_CTX.format(path=path, issue=issue[:4000], tests=", ".join(ftp_names[:4]),
                                   feedback=fb, ctx=ctx[:16000], editfmt=EDIT_FMT)
        try:
            resp = _llm(model, prompt, timeout=300, retries=2)
        except Exception as e:
            failures.append(f"(LLM error {repr(e)[:60]})"); continue
        edits = parse_edits(resp)
        if not edits:
            failures.append("(no valid SEARCH/REPLACE blocks — follow the format exactly)"); continue
        new, edited = apply_edits(orig, edits)
        if new == orig:
            failures.append("(the SEARCH text did not match the file byte-for-byte; copy it exactly)"); continue
        fp = os.path.join(tempfile.gettempdir(), f"ra_{re.sub(r'[^a-z0-9]','_',cont)}.src")
        open(fp, "w", encoding="utf-8").write(new); egl.docker("cp", fp, f"{cont}:/testbed/{path}"); os.unlink(fp)
        ex = egl.docker("exec", cont, "bash", "-lc", run_sh, timeout=400)
        m = re.search(r"RC=(\d+)", ex.stdout or ""); rc = int(m.group(1)) if m else 1
        if rc == 0:
            return {"resolved": True, "rounds_used": rd + 1, "n_edited": len(edited),
                    "loc_has_gold": loc_has_gold, "ctx_n": len(keep)}
        failures.append(ex.stdout.split("\n", 1)[1] if "\n" in ex.stdout else ex.stdout)
    return {"resolved": False, "rounds_used": rounds, "loc_has_gold": loc_has_gold, "ctx_n": len(keep),
            "no_edits": all("no valid" in f or "did not match" in f for f in failures) if failures else True}


def run_sh_for(ftp):
    return RUN_SH.replace("%TESTS%", " ".join(f"'{t}'" for t in ftp[:6]))


def repair_arm(model, issue, orig, path, top_lines, gold, ftp_names, cont, run_sh, W):
    """One repair attempt conditioned on top_lines. Each arm cp's its OWN full modified file (derived from
    the orig string) into the container, overwriting the previous arm's — so no inter-arm reset is needed."""
    olines = orig.splitlines()
    window, keep = windowed(olines, top_lines, W)
    loc_has_gold = bool(keep & gold)
    prompt = REPAIR_WIN.format(path=path, issue=issue[:5000], tests=", ".join(ftp_names[:4]),
                               window=window[:14000], editfmt=EDIT_FMT)
    try:
        resp = _llm(model, prompt, timeout=300, retries=2)
    except Exception as e:
        return {"resolved": False, "error": repr(e)[:100], "loc_has_gold": loc_has_gold, "window_n": len(keep)}
    edits = parse_edits(resp)
    if not edits:
        return {"resolved": False, "no_edits": True, "loc_has_gold": loc_has_gold, "window_n": len(keep)}
    new, edited = apply_edits(orig, edits)
    if new == orig:                                                # SEARCH text never matched -> edit is a no-op
        return {"resolved": False, "edit_no_match": True, "loc_has_gold": loc_has_gold, "window_n": len(keep)}
    fp = os.path.join(tempfile.gettempdir(), f"ra_{re.sub(r'[^a-z0-9]','_',cont)}.src")
    open(fp, "w", encoding="utf-8").write(new); egl.docker("cp", fp, f"{cont}:/testbed/{path}"); os.unlink(fp)
    ex = egl.docker("exec", cont, "bash", "-lc", run_sh, timeout=400)
    m = re.search(r"RC=(\d+)", ex.stdout or ""); rc = int(m.group(1)) if m else 1
    return {"resolved": rc == 0, "n_edited": len(edited), "edited_lines": sorted(edited),
            "loc_has_gold": loc_has_gold, "window_n": len(keep)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--loc-run", required=True, help="egl_e2e run json WITH per-instance `ranks` dump (--dump-ranks)")
    ap.add_argument("--arms", nargs="+", default=["vote", "m5"], choices=["vote", "m5", "m5vb"])
    ap.add_argument("--k", type=int, default=3, help="top-K localized lines to condition repair on")
    ap.add_argument("--window", type=int, default=30, help="+-W fallback window (module-level / oversized fn)")
    ap.add_argument("--context", default="function", choices=["function", "window"],
                    help="repair context: enclosing FUNCTION of the localized lines (default), or a +-W window")
    ap.add_argument("--rounds", type=int, default=3, help="feedback-loop rounds (1 = single-shot)")
    ap.add_argument("--ctx-cap", type=int, default=250, help="max lines of an enclosing function before falling back to a window")
    ap.add_argument("--dataset", default=os.environ.get("SWEBENCH_DATASET", "lite"))
    ap.add_argument("--out", default=str(HERE / "runs" / "repair_ab.json"))
    ap.add_argument("--smoke", type=int, default=0, help="only run first N instances (pipeline check)")
    ap.add_argument("--keep-images", action="store_true")
    args = ap.parse_args()
    model = os.environ.get("MODEL", "deepseek-ai/DeepSeek-V3")
    ARM_KEY = {"vote": "vote_only", "m5": "ours_m5", "m5vb": "ours_m5_votebase"}

    rows = {r["instance_id"]: r for r in p0.load_rows(500, args.dataset)}
    loc = json.load(open(args.loc_run))["results"]
    loc = [r for r in loc if r.get("ranks") and r.get("gold_flat")]
    if args.smoke:
        loc = loc[:args.smoke]
    out = Path(args.out); out.parent.mkdir(exist_ok=True)
    results = json.loads(out.read_text())["results"] if out.exists() else []
    by_id = {r["instance_id"]: r for r in results}
    print(f"[repair_ab] {len(loc)} instances; arms={args.arms}; model={model}; K={args.k} W={args.window}", file=sys.stderr)

    for lr in loc:
        iid = lr["instance_id"]
        if by_id.get(iid, {}).get("done"):
            print(f"{iid} cached", file=sys.stderr); continue
        r = rows.get(iid)
        if not r:
            continue
        ranks = lr["ranks"]; gold = {tuple(x) for x in lr["gold_flat"]}
        path = lr["gold_flat"][0][0]
        gold_ln = {ln for f, ln in gold if f == path}
        try:
            orig = p0.fetch_file(r["repo"], r["base_commit"], path)
        except Exception as e:
            by_id[iid] = {"instance_id": iid, "fetch_error": repr(e)[:80]}; continue
        ftp = r.get("FAIL_TO_PASS")
        if isinstance(ftp, str):
            try: ftp = json.loads(ftp)
            except Exception: ftp = [ftp]
        ftp = ftp or []
        issue = r.get("problem_statement") or ""
        rec = {"instance_id": iid, "repo": r["repo"], "path": path, "n_gold": len(gold_ln), "arms": {}}
        tag = egl.img_tag(iid); cont = "ra_" + re.sub(r'[^a-z0-9_]', '_', iid.lower())
        try:
            if egl.docker("image", "inspect", tag).returncode != 0:
                if egl.docker("pull", tag, timeout=1800).returncode != 0:
                    by_id[iid] = {"instance_id": iid, "pull_error": tag};
                    out.write_text(json.dumps({"results": list(by_id.values())}, indent=2)); continue
            egl.docker("rm", "-f", cont); egl.docker("run", "-d", "--name", cont, tag, "sleep", "infinity")
            try:
                ptxt = (r.get("test_patch") or "").replace("\r\n", "\n")
                if not ptxt.endswith("\n"): ptxt += "\n"
                tp = os.path.join(tempfile.gettempdir(), f"ra_{iid.replace('/','_')}.patch")
                open(tp, "wb").write(ptxt.encode()); egl.docker("cp", tp, f"{cont}:/tmp/test.patch"); os.unlink(tp)
                egl.docker("exec", cont, "bash", "-lc", SETUP_SH.replace("%MIRROR%", MIRROR), timeout=400)
                run_sh = run_sh_for(ftp)
                g = cg.CodeGraph(orig, path)
                for arm in args.arms:
                    key = ARM_KEY[arm]
                    ranked = [ln for f, ln in (tuple(x) for x in ranks.get(key, [])) if f == path]
                    if not ranked:
                        rec["arms"][arm] = {"resolved": False, "no_localization": True}; continue
                    if args.context == "function" or args.rounds > 1:
                        rec["arms"][arm] = repair_arm_loop(model, issue, orig, path, ranked[:args.k], gold_ln,
                                                           ftp, cont, run_sh, args.rounds, g, args.window, args.ctx_cap)
                    else:
                        rec["arms"][arm] = repair_arm(model, issue, orig, path, ranked[:args.k], gold_ln,
                                                      ftp, cont, run_sh, args.window)
                    print(f"  {iid} [{arm}] resolved={rec['arms'][arm].get('resolved')} "
                          f"loc_has_gold={rec['arms'][arm].get('loc_has_gold')} "
                          f"rounds={rec['arms'][arm].get('rounds_used','-')}", file=sys.stderr)
            finally:
                egl.docker("rm", "-f", cont)
                if not args.keep_images: egl.docker("rmi", tag)
            rec["done"] = True
        except Exception as e:
            rec["error"] = repr(e)[:200]
        by_id[iid] = rec
        out.write_text(json.dumps({"results": list(by_id.values())}, indent=2), encoding="utf-8")

    # ---- summary: resolved rate per arm + paired McNemar (m5 vs vote) ----
    done = [r for r in by_id.values() if r.get("done")]
    summ = {"n": len(done), "model": model, "context": args.context, "rounds": args.rounds,
            "k": args.k, "window": args.window, "arms": {}}
    for arm in args.arms:
        rr = [1 if r["arms"].get(arm, {}).get("resolved") else 0 for r in done if arm in r.get("arms", {})]
        lg = [1 if r["arms"].get(arm, {}).get("loc_has_gold") else 0 for r in done if arm in r.get("arms", {})]
        summ["arms"][arm] = {"n": len(rr), "resolved_rate": round(100 * sum(rr) / len(rr), 1) if rr else None,
                             "loc_has_gold_rate": round(100 * sum(lg) / len(lg), 1) if lg else None}
    if "vote" in args.arms and "m5" in args.arms:
        pairs = [(1 if r["arms"].get("m5", {}).get("resolved") else 0,
                  1 if r["arms"].get("vote", {}).get("resolved") else 0)
                 for r in done if "m5" in r.get("arms", {}) and "vote" in r.get("arms", {})]
        w, l, disc, p = sp.mcnemar(pairs); m, lo, hi = sp.boot_ci([a - b for a, b in pairs])
        summ["m5_vs_vote_resolve"] = {"delta_pp": round(100 * m, 1), "ci": [round(100 * lo, 1), round(100 * hi, 1)],
                                      "mcnemar": {"w": w, "l": l, "disc": disc, "p": round(p, 4)}, "n": len(pairs)}
    d = json.loads(out.read_text()); d["summary"] = summ; out.write_text(json.dumps(d, indent=2), encoding="utf-8")
    print("\n==== REPAIR A/B SUMMARY ====\n" + json.dumps(summ, indent=2), file=sys.stderr)


if __name__ == "__main__":
    main()
