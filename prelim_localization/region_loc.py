#!/usr/bin/env python3
"""region_loc — REGION-narrowed line localization, the validated fix for the real
multi-file bottleneck: the LLM cannot pinpoint lines in a 1000-9000-line file (P0-big
precision wall), but it can in a ~200-line region. Diagnosis (hybrid_loop_agentic_full):
gold files median 1895 lines -> S2 line recall 0.107 even with the file GIVEN IN FULL.

Two stages, borrowing SOTA element-localization:
  (1) ELEMENT SELECTION (Agentless skeleton): show the LLM the file's class/function
      SKELETON (signatures + line spans, ~10% LoC) and ask which elements need editing
      -> high region-recall at tiny prompt cost; UNION with graph/coverage-ranked
      functions so a missed name is backstopped.
  (2) LINE LOCALIZATION WITHIN REGIONS + SELF-CONSISTENCY: numbered view of only the
      selected regions; draw k samples and UNION predicted lines (P5: union recall
      0.53->0.68). Coverage-executed regions are prioritized.

This module is import-safe and has a __main__ scaled validation:
  OPENAI_BASE_URL=... MODEL=... python region_loc.py --sample 13   # file-given, no Docker
"""
from __future__ import annotations
import argparse, json, os, re, ssl, sys, time, urllib.request
from pathlib import Path
import p0_line_recall as p0
import code_graph as cg
from hybrid_loop import _llm, RANK_PROMPT, parse_ranked

HERE = Path(__file__).resolve().parent
_CTX = ssl.create_default_context()

def _llm_t(model, prompt, temperature=0.0, timeout=90, retries=2):
    """Temperature-capable OpenAI-compatible call (hybrid_loop._llm is temp=0 only, so
    its k 'self-consistency' samples were near-identical; temp>0 gives real diversity).
    timeout is short (outputs are short ranked-line JSON) so a HUNG connection fails fast
    and retries — a 300s timeout stalled the agentic harness ~15 min per dropped socket."""
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    key = p0._openai_key()
    payload = {"model": model, "temperature": temperature, "messages": [{"role": "user", "content": prompt}]}
    if any(x in model.lower() for x in ("v4", "glm")):   # reasoning-by-default -> disable for batch speed
        payload["thinking"] = {"type": "disabled"}
    body = json.dumps(payload).encode()
    for a in range(retries):
        try:
            req = urllib.request.Request(base + "/chat/completions", data=body,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
            return json.loads(urllib.request.urlopen(req, timeout=timeout, context=_CTX).read())["choices"][0]["message"]["content"]
        except Exception:
            if a == retries - 1: raise
            time.sleep(min(20, 4 * (a + 1)))

ELEMENT_PROMPT = """You are localizing which CODE ELEMENTS (functions/methods/classes) in ONE large file must be edited to resolve a GitHub issue.

## Issue
{issue}

## File: {path}  ({nlines} lines) — structural skeleton (signatures + line ranges only)
{skeleton}

## Task
List the function/method/class NAMES most likely to need editing (most-likely first), up to 8.
Output ONLY a JSON array of names, e.g. ["fit","_validate_input","BaseClass"]. JSON only."""

# Stage-B vote prompt — RECALL-FAVORING (the Stage-B tuning): ask for ALL plausible lines up to a
# LARGER cap so big-gold files aren't truncated at 15; a later RRF stage re-ranks for precision.
REGION_RANK_PROMPT = """You are localizing the exact code lines that must be edited to resolve a GitHub issue, within a NARROWED suspect region of one file.

## Issue
{issue}

## File: {path} — numbered lines of the suspect region
{numbered}

## Task
List ALL line numbers that plausibly need editing, RANKED most-likely first. FAVOR RECALL: include every line you are even somewhat unsure about (a later stage re-ranks for precision, so over-inclusion is fine, omission is costly).
Output ONLY a JSON array of line numbers (most-likely first), up to {cap}, e.g. [88, 89, 42]. JSON only."""

def parse_names(text):
    m = re.search(r"\[.*?\]", text, re.S)
    if m:
        try: return [str(x) for x in json.loads(m.group(0)) if isinstance(x, str)]
        except Exception: pass
    return re.findall(r'"([A-Za-z_][A-Za-z0-9_]*)"', text)

def select_regions(model, issue, src, path, g, coverage_lines=None, max_funcs=8,
                   graph_backstop=4, n_elem=2, elem_temp=0.5, module_lines=12, all_module=False):
    """Stage 1 (RECALL-first over-selection): UNION of
      (a) n_elem MULTI-SAMPLE LLM element selections from the skeleton (self-consistency
          over WHICH functions -> recovers gold functions a single pass misses),
      (b) graph+coverage rank_functions backstop,
      (c) MODULE-LEVEL suspect lines (gold outside any function: parse tables, class-body
          assignments) — these were structurally unreachable before.
    Returns (region_line_set, chosen_function_dicts)."""
    chosen = {}
    by_name = {}
    for f in g.funcs:
        by_name.setdefault(f["name"], f)
        by_name.setdefault((f.get("class") or "") + "." + f["name"], f)
    skel = g.skeleton(max_funcs=120)
    names = set()
    for s in range(max(1, n_elem)):
        try:
            for nm in parse_names(_llm_t(model, ELEMENT_PROMPT.format(
                    issue=issue, path=path, nlines=g.nlines, skeleton=skel),
                    temperature=0.0 if s == 0 else elem_temp))[:max_funcs]:
                names.add(nm)
        except Exception:
            pass
    for nm in names:
        f = by_name.get(nm) or by_name.get("." + nm)
        if f: chosen[(f["start"], f["end"])] = f
    for c in g.classes:
        if c["name"] in names and (c["end"] - c["start"]) <= 120:
            chosen[(c["start"], c["end"])] = {"name": c["name"], "start": c["start"], "end": c["end"]}
    for f in g.rank_functions(issue, "", coverage_lines=coverage_lines, topn=graph_backstop):
        chosen[(f["start"], f["end"])] = f
    region = set()
    for (s, e) in chosen: region |= set(range(s, e + 1))
    # (c) module-level suspect lines (not inside any function) — issue-token + coverage scored
    issue_toks = set(cg.tokenize(issue))
    cov = set(coverage_lines or [])
    mod = []
    lines = src.splitlines()
    if all_module:                                  # Lever 2: recall-complete — EVERY module-level code line
        for i, ln in enumerate(lines, 1):           # (imports/class-body/decorators are 9% of gold, often missed)
            s = ln.strip()
            if s and not s.startswith("#") and g.line_func.get(i) is None:
                region.add(i)
        return region, list(chosen.values())
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if not s or s.startswith("#") or g.line_func.get(i) is not None:
            continue
        sc = len(set(cg.tokenize(ln)) & issue_toks) + (1.5 if i in cov else 0)
        if sc > 0: mod.append((sc, i))
    mod.sort(key=lambda x: -x[0])
    for _, i in mod[:module_lines]:
        region |= set(range(max(1, i - 2), min(len(lines), i + 2) + 1))
    return region, list(chosen.values())

def _make_region(model, issue, src, path, g, lines, coverage_lines, failure,
                 max_region_lines=900, small_file=500, cfg=None):
    """Stage 1 region construction (the recall-CEILING substrate, shared by every
    head-to-head variant). Small files (<= small_file) skip narrowing -> whole executable
    file (region_loc is then a strict improvement over whole-file).
    cfg (E6 ablation; None/{} = byte-identical shipped Stage-1) toggles the constructs:
    small_file (whole-file bypass threshold), n_elem (element self-consistency), graph_backstop,
    module_lines."""
    cfg = cfg or {}
    small_file = cfg.get("small_file", small_file)
    max_region_lines = cfg.get("max_region_lines", max_region_lines)   # Lever 2: raise/disable to stop truncating whole-file regions
    if len(lines) <= small_file:
        region = {i for i, l in enumerate(lines, 1) if l.strip() and not l.strip().startswith("#")}
    else:
        region, _ = select_regions(model, issue, src, path, g, coverage_lines,
                                   n_elem=cfg.get("n_elem", 2),
                                   graph_backstop=cfg.get("graph_backstop", 4),
                                   module_lines=cfg.get("module_lines", 12),
                                   all_module=cfg.get("all_module", False))   # Lever 2: include ALL module-level code lines
    region = {ln for ln in region if 1 <= ln <= len(lines)}
    if len(region) > max_region_lines:        # budget: keep top graph-scored region lines
        scores, _ = g._line_scores(issue, failure, coverage_lines)
        region = set(sorted(region, key=lambda ln: -scores.get(ln, 0))[:max_region_lines])
    return region

def _vote(model, issue, path, lines, region, k_samples, lines_cap=30, temp_sched=True, region_filter=True):
    """Stage 2 RR-vote (Stage-B TUNED for recall): k samples drawn with a TEMPERATURE SCHEDULE
    (sample 0 greedy, the rest spread over [0.5,1.0] for genuine diversity -> a bigger
    self-consistency UNION), a LARGER per-sample line cap (`lines_cap`, so big-gold files aren't
    truncated at 15), and a recall-favoring prompt. reciprocal-rank vote -> {line: vote_mass}.
    The union of voted lines is the recall set; k and lines_cap directly lift that union.
    temp_sched=False (E6 ablation) -> all samples greedy (temp=0), killing vote diversity."""
    numbered = "\n".join(f"{ln}: {lines[ln-1]}" for ln in sorted(region))
    prompt = REGION_RANK_PROMPT.format(issue=issue, path=path, numbered=numbered, cap=lines_cap)
    freq = {}; counts = {}
    k = max(1, k_samples)
    for s in range(k):
        temp = (0.0 if s == 0 else min(1.0, 0.5 + 0.5 * ((s - 1) / max(1, k - 2)))) if temp_sched else 0.0
        try:
            voted_this = set()
            for r, p in enumerate(parse_ranked(_llm_t(model, prompt, temperature=temp))):
                # region_filter=False (Q3 set-expansion) admits in-FILE votes just outside the shown
                # region (off-by-a-few neighbors, max_region_lines-evicted lines) -> bigger union.
                if (p in region) if region_filter else (1 <= p <= len(lines)):
                    freq[p] = freq.get(p, 0) + 1.0 / (1 + r); voted_this.add(p)
            for p in voted_this:                       # cross-sample CONSENSUS: #samples that voted p
                counts[p] = counts.get(p, 0) + 1
        except Exception:
            pass
    return freq, counts

def _expand_voted(g, freq, region, depth=1, total_cap=25):
    """Q3 SET-EXPANSION (raises voted_ceiling, NOT a re-rank): grow the voted set with def-use
    slice neighbors of the voted lines that fall inside the region. Adds candidates the LLM never
    named — the def a buggy line READS, or the guard that CONSUMES its value, one+ def-use hop away.
    This is the only structural lever per the diagnosis (the vote freezes the set; everything else
    only re-orders). Returns ONLY the new lines. cap accounts for seeds so total_cap really bounds
    the growth. Multi-line statements are materialized via g._stmt_end."""
    if not g.ok or not freq:
        return set()
    seeds = {g.stmt_line.get(p, p) for p in freq}
    grown = g.dataflow_slice(seeds, direction="both", depth=depth, cap=len(seeds) + total_cap)
    add = set()
    for s in grown:
        end = g._stmt_end(s) if hasattr(g, "_stmt_end") else s
        for ln in range(s, end + 1):
            if ln in region and ln not in freq:
                add.add(ln)
    return add

def _rank_v0(freq, scores, counts=None, K=20):
    """V0 Stage-B re-rank — RECALL-MONOTONE (reorders the voted set, NEVER drops). RRF fusion of
    THREE signals (the ARISE-targeting tune for Line R@k@1/@10):
      (1) RR-vote mass `freq`;
      (2) GRADED def-use-slice graph score `scores` (line_scores_v2 — ARISE's active line-ranking
          ingredient, "+7 Line R@1"; production previously used the BINARY slice, under-using it);
      (3) CROSS-SAMPLE CONSENSUS `counts` (a line ALL k samples agree on is high-confidence -> a
          strong top-1 signal).
    K lowered 30->20 for a SHARPER top (more separation among the top-ranked lines)."""
    voted = list(freq)
    vr = {ln: i for i, ln in enumerate(sorted(voted, key=lambda k: -freq[k]))}
    gr = {ln: i for i, ln in enumerate(sorted(voted, key=lambda k: -scores.get(k, 0.0)))}
    cr = ({ln: i for i, ln in enumerate(sorted(voted, key=lambda k: -counts.get(k, 0)))}
          if counts else None)
    def score(ln):
        s = 1.0 / (K + vr[ln]) + 1.0 / (K + gr[ln])
        if cr is not None: s += 1.0 / (K + cr[ln])
        return s
    return sorted(voted, key=lambda ln: -score(ln))

def _tiebreak(ln):
    """Knuth multiplicative hash -> a line-POSITION-decorrelated tiebreak, so equal-score voted
    lines aren't ordered by ascending line index (which silently flatters low-line-number bugs)."""
    return (ln * 2654435761) % (2 ** 32)

def _rank_counts(freq, scores, counts, K=20):
    """Consensus-PRIMARY re-rank (the R@1 candidate). Diagnosis: the voted set CONTAINS the gold
    line ~85% of the time, but the equal-weight RRF (_rank_v0) ranks it #1 only ~38% -> the top-1
    signal is too diffuse. Cross-sample agreement `counts` (#samples that INDEPENDENTLY voted a
    line) is the natural top-1 confidence: a line all k samples pick is the strongest single bet.
    Order: counts desc -> RR-vote mass desc -> graded graph score desc -> hash tiebreak. RECALL-
    MONOTONE (reorders the voted set, never drops) so the R@10 ceiling is identical to v0."""
    counts = counts or {}
    voted = list(freq)
    return sorted(voted, key=lambda ln: (-counts.get(ln, 0), -freq.get(ln, 0.0),
                                         -scores.get(ln, 0.0), _tiebreak(ln)))

def region_line_loc(model, issue, src, path, coverage_lines=None, k_samples=5,
                    failure="", max_region_lines=900, small_file=500, lines_cap=30):
    """Stage 1 + Stage 2 (the production V0, Stage-B TUNED: k_samples=5 + lines_cap=30 +
    temp-scheduled union for higher within-region recall). Returns (ranked_lines, region, n)."""
    g = cg.CodeGraph(src, path)
    if not g.ok:
        return [], set(), 0
    lines = src.splitlines()
    region = _make_region(model, issue, src, path, g, lines, coverage_lines, failure,
                          max_region_lines, small_file)
    freq, counts = _vote(model, issue, path, lines, region, k_samples, lines_cap)
    if not freq:
        return [], region, len(region)
    # GRADED def-use-slice score (ARISE's active line-ranking ingredient) for the rank, not binary
    scores = g.line_scores_v2(issue, failure, coverage_lines, graded=True, use_coverage=bool(coverage_lines))
    return _rank_v0(freq, scores, counts), region, len(region)

def region_line_loc_ex(model, issue, src, path, coverage_lines=None, k_samples=5,
                       failure="", max_region_lines=900, small_file=500, lines_cap=30,
                       rank_mode="v0", cfg=None):
    """region_line_loc + the persisted substrate, computed in ONE vote pass (so a --dump-substrate
    run yields the metric AND free offline-ablation material without paying for the vote twice).
    Returns (ranked_lines, substrate) where substrate = {region, n_region, freq, counts}.
    rank_mode: 'v0' (shipped equal-RRF, byte-identical ranking) | 'counts' (consensus-primary).
    cfg (E6 Stage-B construct ablation; None/{} = shipped behavior) overrides region/vote knobs."""
    cfg = cfg or {}
    k_samples = cfg.get("k_samples", k_samples)
    lines_cap = cfg.get("lines_cap", lines_cap)
    g = cg.CodeGraph(src, path)
    if not g.ok:
        return [], None
    lines = src.splitlines()
    region = _make_region(model, issue, src, path, g, lines, coverage_lines, failure,
                          max_region_lines, small_file, cfg=cfg)
    freq, counts = _vote(model, issue, path, lines, region, k_samples, lines_cap,
                         temp_sched=cfg.get("temp_sched", True),
                         region_filter=not cfg.get("vote_unfiltered", False))
    if freq and cfg.get("grow_depth"):                  # Q3 def-use SET-EXPANSION (gated; default OFF)
        grown = _expand_voted(g, freq, region, depth=cfg.get("grow_depth", 1),
                              total_cap=cfg.get("grow_cap", 25))
        base = min(freq.values())
        for ln in grown:
            freq.setdefault(ln, base * 1e-3)            # new candidate, sub-minimal vote mass (tail)
    sub = {"region": sorted(region), "n_region": len(region),
           "freq": {int(k): round(v, 6) for k, v in freq.items()},
           "counts": {int(k): int(v) for k, v in counts.items()}}
    if not freq:
        return [], sub
    scores = g.line_scores_v2(issue, failure, coverage_lines, graded=True, use_coverage=bool(coverage_lines))
    ranked = _rank_counts(freq, scores, counts) if rank_mode == "counts" else _rank_v0(freq, scores, counts)
    return ranked, sub

def region_substrate(model, issue, src, path, coverage_lines=None, k_samples=5, failure="", lines_cap=30):
    """The LLM-EXPENSIVE head-to-head substrate: Stage-A region + ONE RR-vote, drawn once
    per file and PERSISTED so every ranking/pruning variant (V0 / vote-only / ARISE /
    ARISE-standalone / SieveFL) re-applies OFFLINE from the identical voted set without
    re-spending the LLM. The rankers themselves live in egl_headtohead.py (kept out of the
    production path so `region_line_loc` stays byte-identical to the shipped V0)."""
    g = cg.CodeGraph(src, path)
    if not g.ok:
        return None
    lines = src.splitlines()
    region = _make_region(model, issue, src, path, g, lines, coverage_lines, failure)
    freq, counts = _vote(model, issue, path, lines, region, k_samples, lines_cap)
    return {"region": sorted(region), "n_region": len(region),
            "freq": {int(k): round(v, 4) for k, v in freq.items()},
            "counts": {int(k): v for k, v in counts.items()}}


FINAL_PICK_PROMPT = """You are pinpointing the exact line(s) to edit to resolve a GitHub issue, choosing from a SHORTLIST already narrowed by a prior stage.

## Issue
{issue}

## File: {path} — candidate lines (each shown with a little surrounding context)
{candidates}

## Task
Re-rank ONLY these candidate line numbers, from MOST to least likely to be the exact edit location.
Output ONLY a JSON array of the line numbers (most-likely first), e.g. [88, 42, 90]. JSON only."""

def llm_final_pick(model, issue, path, lines, ranked, top_n=8, ctx=1):
    """R@1-targeting final精排 (one focused LLM call): take the top_n ranked candidates, show each
    with a little context, and let the LLM RE-RANK just those. Returns (LLM-reordered head) + tail,
    so only the HEAD changes -> R@1/R@5 can lift while the R@10 tail/ceiling is preserved. Falls
    back to the input `ranked` on any error/empty parse (never regresses the candidate set)."""
    head = ranked[:top_n]
    if len(head) <= 1:
        return ranked
    block = []
    for ln in head:
        lo = max(1, ln - ctx); hi = min(len(lines), ln + ctx)
        snip = " | ".join(f"{i}:{lines[i-1].strip()[:80]}" for i in range(lo, hi + 1))
        block.append(f"[{ln}] {snip}")
    try:
        picked = [p for p in parse_ranked(_llm_t(model, FINAL_PICK_PROMPT.format(
            issue=issue[:4000], path=path, candidates="\n".join(block)), temperature=0.0)) if p in head]
    except Exception:
        return ranked
    if not picked:
        return ranked
    reordered = picked + [ln for ln in head if ln not in picked]
    return reordered + ranked[top_n:]

# ------------------------------- validation ----------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=13)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--broad", action="store_true", help="ALL Verified Python instances (single+multi, all repos) for the 150-300 significance run")
    ap.add_argument("--min-file-lines", type=int, default=0, help="only instances whose largest gold file exceeds this (focus where region-narrowing applies)")
    ap.add_argument("--out", default=str(HERE / "region_loc_validation.json"))
    args = ap.parse_args()
    model = os.environ.get("MODEL", "deepseek-ai/DeepSeek-V3")
    PY = {"astropy/astropy","scikit-learn/scikit-learn","pydata/xarray","psf/requests","matplotlib/matplotlib","pallets/flask"}
    rows = {r["instance_id"]: r for r in p0.load_rows(500)}
    import random
    cands = []
    for iid, r in rows.items():
        files = p0.parse_patch(r.get("patch") or "")
        py = [f for f in files if f.endswith(".py") and files[f]["hunks"]]
        if not py or len(py) != len([f for f in files if f.endswith(".py")]):
            continue
        if args.broad:                          # all repos, single+multi-file
            cands.append(iid)
        elif r["repo"] in PY and len(py) >= 2 and r.get("FAIL_TO_PASS"):
            cands.append(iid)
    random.Random(0).shuffle(cands)             # deterministic, repo-diverse
    if args.min_file_lines:                     # keep only instances with a large gold file
        kept = []
        for iid in cands:
            r = rows[iid]; files = p0.parse_patch(r.get("patch") or "")
            big = False
            for gf in [f for f in files if f.endswith(".py")]:
                try:
                    if len(p0.fetch_file(r["repo"], r["base_commit"], gf).splitlines()) > args.min_file_lines:
                        big = True; break
                except Exception: pass
            if big: kept.append(iid)
            if len(kept) >= args.sample: break
        cands = kept
    cands = cands[:args.sample]
    KS = (1, 5, 10)
    res = []
    for iid in cands:
        r = rows[iid]; files = p0.parse_patch(r.get("patch") or ""); issue = (r.get("problem_statement") or "")[:5000]
        gold_files = [f for f in files if f.endswith(".py")]
        tot_gold = sum(len(files[f]["region"]) for f in gold_files)
        whole_hit = reg_hit = 0; reg_ranked_global = []; whole_ranked_global = []; reg_recall_sum = 0
        for gf in gold_files:
            gold = files[gf]["region"]
            try: src = p0.fetch_file(r["repo"], r["base_commit"], gf)
            except Exception: continue
            lines = src.splitlines()
            # whole-file baseline (no region narrowing), file given fully
            if len(lines) <= 4000:
                numbered = "\n".join(f"{i+1}: {l}" for i, l in enumerate(lines))
                try: wp = parse_ranked(_llm(model, RANK_PROMPT.format(issue=issue, path=gf, numbered=numbered)))
                except Exception: wp = []
            else: wp = []
            whole_hit += len(set(wp) & gold); whole_ranked_global += [(gf, p) for p in wp]
            # region-narrowed + self-consistency
            rp, region, _ = region_line_loc(model, issue, src, gf, k_samples=args.k)
            reg_hit += len(set(rp) & gold); reg_ranked_global += [(gf, p) for p in rp]
            reg_recall_sum += (len(gold & region) / len(gold)) if gold else 0
        goldflat = {(f, ln) for f in gold_files for ln in files[f]["region"]}
        def hitk(rk, k): return 1 if (set(rk[:k]) & goldflat) else 0
        rec = {"instance_id": iid, "n_gold_files": len(gold_files), "tot_gold": tot_gold,
               "whole_recall": round(whole_hit / tot_gold, 3) if tot_gold else 0,
               "region_recall": round(reg_hit / tot_gold, 3) if tot_gold else 0,
               "region_ceiling": round(reg_recall_sum / len(gold_files), 3) if gold_files else 0,
               **{f"whole_R@{k}": hitk(whole_ranked_global, k) for k in KS},
               **{f"region_R@{k}": hitk(reg_ranked_global, k) for k in KS}}
        res.append(rec)
        print(f"{iid:30s} whole={rec['whole_recall']} region={rec['region_recall']} "
              f"(ceiling {rec['region_ceiling']}) | R@5 whole={rec['whole_R@5']} region={rec['region_R@5']}",
              file=sys.stderr); sys.stderr.flush()
        Path(args.out).write_text(json.dumps({"results": res}, indent=2), encoding="utf-8")
    import statistics as st
    def m(k): return round(st.mean(x[k] for x in res), 3)
    def Rk(k): return round(100 * st.mean(x[k] for x in res), 1)
    summary = {"n": len(res), "whole_recall": m("whole_recall"), "region_recall": m("region_recall"),
               "region_ceiling": m("region_ceiling"),
               "whole_R@k": {k: Rk(f"whole_R@{k}") for k in KS},
               "region_R@k": {k: Rk(f"region_R@{k}") for k in KS}}
    d = json.loads(Path(args.out).read_text()); d["summary"] = summary
    Path(args.out).write_text(json.dumps(d, indent=2), encoding="utf-8")
    print("\n==== SUMMARY (LINE recall, file given) ====\n" + json.dumps(summary, indent=2), file=sys.stderr)

if __name__ == "__main__":
    main()
