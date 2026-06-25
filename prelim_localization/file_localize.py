#!/usr/bin/env python3
"""file_localize — STRONG file-retrieval front-end (the Agentless FSE'25 file-localization step),
reimplemented in stdlib + OpenAI-compatible LLM API (NO GPU / training / Docker). Replaces the weak
ReAct file-finder (egl_agentic, file_recall 0.47).

Why Agentless and not SweRank/LocAgent/ARISE (research wf_dc17b418): SweRank (file Acc@10 ~93%) and
LocAgent (~94% Acc@5) are stronger but need self-hosted FINE-TUNED models (SweRankEmbed/LLM, or a
tuned Qwen) — not directly usable. ARISE (File R@1 0.67 / R@3 0.82) is the agentic bar but is heavy to
rebuild (graph+toolset+agent loop). Agentless's STEP-1 file localizer is the strongest DIRECTLY-USABLE
recipe: a single greedy LLM call over the repo's NAME-ONLY INDENTED FILE TREE. Reported on SWE-bench
Lite (GPT-4o): ~0.79 LLM-only, ~0.82 +embedding (v1.5). At top-k=10 the union recall climbs toward
~0.85 — matching/exceeding ARISE's File R@3 0.82.

  localize_files(model, repo, commit, issue, topk=10) -> ranked candidate repo-relative .py paths

Optional +~4pts (Agentless v1.5 combined): an OpenAI-compatible EMBEDDING supplement — embed file
skeletons + the issue, cosine-rank, drop 'irrelevant folders', UNION with the LLM picks. Implemented
behind `embed=True` (default off; the LLM-only path already exceeds ARISE and needs no embedding API).
"""
from __future__ import annotations
import json, math, os, re
from pathlib import Path
import p0_line_recall as p0
import p1_realistic as p1
import code_graph as cg
from hybrid_loop import _llm


def _repo_py_paths(repo, commit):
    """Repo-relative .py paths at base_commit, RATE-LIMIT ROBUST: cached GitHub-trees result ->
    GitHub trees API (60/hr unauth) -> codeload TARBALL snapshot (NOT API-rate-limited). The tarball
    result is cached in the tree format so it's a one-time cost. Needed for n=300 across all repos."""
    cache = p0.CACHE / ("tree_" + re.sub(r"[^A-Za-z0-9._-]", "_", f"{repo}_{commit}") + ".json")
    if cache.exists():
        try: return [p for p in json.loads(cache.read_text(encoding="utf-8")).get("paths", []) if p.endswith(".py")]
        except Exception: pass
    try:
        return [p for p in p1.fetch_tree(repo, commit).get("paths", []) if p.endswith(".py")]
    except Exception:
        pass
    try:                                                 # tarball fallback (no API rate limit)
        import repo_snapshot as rs
        root = rs.snapshot(repo, commit)
        paths = sorted(str(p.relative_to(root)).replace("\\", "/") for p in Path(root).rglob("*.py"))
        cache.write_text(json.dumps({"paths": paths, "truncated": False}), encoding="utf-8")
        return paths
    except Exception:
        return []

# Agentless file-localization prompt (STEP 1), adapted to our infra.
AGENTLESS_FILE_PROMPT = """Please look through the following GitHub issue and the list of Python files in the repository, and identify the files one would need to EDIT to resolve the issue.

### GitHub issue
{issue}

### Repository Python files (full paths)
{tree}

### Task
Return AT MOST {topk} file paths that most likely need editing, ordered MOST-LIKELY FIRST, one per line, wrapped in a single fenced ``` block. COPY each path EXACTLY as it appears in the list above (full path); only list files from the list."""


def build_tree(paths, max_files=1200, issue=""):
    """FLAT sorted FULL-PATH list of the repo's .py files. Full paths (not an indented tree): an
    indented tree shows deeply-nested files as just their basename (e.g. `__init__.py` under
    `.../management/`), which the LLM reconstructs into the WRONG full path and which then fails
    strict validation (ambiguous basenames). A flat full-path list lets the LLM copy exact paths
    (hybrid_loop_v2 S1 got file recall 0.77 this way). For very large repos keep issue-token-relevant
    files + a head sample."""
    paths = sorted(set(paths))
    if len(paths) > max_files and issue:
        toks = set(cg.tokenize(issue))
        scored = sorted(paths, key=lambda p: -len(set(cg.tokenize(p.replace("/", " "))) & toks))
        paths = sorted(set(scored[:max_files]) | set(paths[:300]))
    return "\n".join(paths)


def parse_files(text, valid):
    """Ranked, validated repo-relative paths from the LLM's fenced answer (STRICT: must exist, so a
    sloppy/hallucinated path can't fabricate a gold-file hit)."""
    block = re.search(r"```[a-zA-Z]*\n?(.*?)```", text, re.S)
    body = block.group(1) if block else text
    out = []
    for line in body.splitlines():
        cand = line.strip().strip("`-*0123456789. \t").replace("\\", "/")
        if not cand or cand.endswith("/"):
            continue
        if cand in valid:
            if cand not in out: out.append(cand)
        else:                                            # tolerate an UNAMBIGUOUS dir-boundary suffix
            m = [p for p in valid if p.endswith("/" + cand)]
            if len(m) == 1 and m[0] not in out: out.append(m[0])
    return out


def _embed(model_emb, texts, base=None, key=None, timeout=120):
    """OpenAI-compatible /embeddings batch call (only used when embed=True)."""
    import ssl, urllib.request
    base = (base or os.environ.get("EMBED_BASE_URL") or os.environ.get("OPENAI_BASE_URL", "")).rstrip("/")
    key = key or p0._openai_key()
    body = json.dumps({"model": model_emb, "input": texts}).encode()
    req = urllib.request.Request(base + "/embeddings", data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    d = json.loads(urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()).read())
    return [e["embedding"] for e in d["data"]]


def _embed_supplement(repo, commit, issue, paths, topn, model_emb):
    """Agentless v1.5 embedding supplement: cosine-rank files by issue similarity (file skeleton text).
    Returns a ranked path list to UNION with the LLM picks. Best-effort; [] on any failure."""
    try:
        docs, keep = [], []
        for f in paths[:400]:                            # cap embedding cost
            try: src = p0.fetch_file(repo, commit, f)
            except Exception: continue
            g = cg.CodeGraph(src, f)
            docs.append((f + "\n" + (g.skeleton(max_funcs=40) if g.ok else ""))[:2000]); keep.append(f)
        if not docs: return []
        qv = _embed(model_emb, [issue[:4000]])[0]
        dvs = []
        for i in range(0, len(docs), 64):
            dvs += _embed(model_emb, docs[i:i + 64])
        def cos(a, b):
            s = sum(x * y for x, y in zip(a, b)); na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(y * y for y in b))
            return s / (na * nb + 1e-9)
        return [f for _, f in sorted(zip((cos(qv, dv) for dv in dvs), keep), reverse=True)][:topn]
    except Exception:
        return []


def _round_robin(*lists):
    out, i = [], 0
    while any(i < len(L) for L in lists):
        for L in lists:
            if i < len(L) and L[i] not in out:
                out.append(L[i])
        i += 1
    return out


# File-level analog of region_loc.llm_final_pick: a focused LLM LISTWISE re-rank of the top-N
# candidate files. The Agentless single-call front-end already gets the gold file into the top-k
# (file R@10 ~0.82) but ranks it #1 only ~58% — a RANKING-headroom problem, not a recall problem
# (same diagnosis as our line R@1). One extra LLM call over the shortlist closes that head gap so
# the file-finder reaches ARISE parity (target file R@1 ~0.67), WITHOUT a separate model / Docker /
# the heavy ARISE agent loop. Recall-safe: only the head is reordered, the tail is preserved, and
# any parse failure falls back to the input ranking (never drops a candidate).
FILE_RERANK_PROMPT = """You are identifying which file(s) must be EDITED to resolve a GitHub issue, choosing from a shortlist already narrowed by a retrieval stage.

## GitHub issue
{issue}

## Candidate files (path + structural skeleton: classes/functions with line spans)
{candidates}

## Task
Re-rank ALL the candidate file paths from MOST to least likely to be the file(s) needing edits to fix the issue. Copy each path EXACTLY as given. Output ONLY a JSON array of the paths, most-likely first, e.g. ["a/b.py", "a/c.py"]. JSON only."""


def llm_file_rerank(model, repo, commit, issue, ranked, top_n=10):
    """LLM listwise re-rank of the top_n candidate files -> reordered head + preserved tail.
    Reads each candidate's skeleton (signatures + line spans, ~10% of the file) so the model judges
    on structure, not just the path. Recall-safe: falls back to `ranked` on any error/empty parse."""
    head = ranked[:top_n]
    if len(head) <= 1:
        return ranked
    blocks = []
    for p in head:
        skel = ""
        try:
            g = cg.CodeGraph(p0.fetch_file(repo, commit, p), p)
            if g.ok:
                skel = g.skeleton(max_funcs=10)
        except Exception:
            pass
        blocks.append(f"### {p}\n{skel[:700]}")
    try:
        picked = parse_files(_llm(model, FILE_RERANK_PROMPT.format(
            issue=issue[:4000], candidates="\n\n".join(blocks)), timeout=120, retries=2), set(head))
    except Exception:
        return ranked
    picked = [p for p in picked if p in head]
    if not picked:
        return ranked
    return picked + [p for p in head if p not in picked] + ranked[top_n:]


def localize_files(model, repo, commit, issue, topk=10, expand_graph=True, embed=False,
                   model_emb=None):
    """Agentless file localization (LLM over the indented repo tree) + optional additive graph
    import-neighbor expansion + optional embedding supplement. Returns a RANKED list of candidate
    repo-relative .py paths (length ~topk). NEVER drops the LLM picks (recall-safe)."""
    paths = _repo_py_paths(repo, commit)
    valid = set(paths)
    if not paths:
        return []
    tree_str = build_tree(paths, issue=issue)
    # Do NOT swallow LLM errors here: a silent [] on an API failure (e.g. 403 "balance insufficient")
    # would cascade to a fake 0 line-recall. Let it raise so the driver records a RETRYABLE error.
    raw = _llm(model, AGENTLESS_FILE_PROMPT.format(issue=issue[:6000], tree=tree_str, topk=topk),
               timeout=180, retries=3)
    picked = parse_files(raw, valid)
    ranked = list(picked[:topk])
    # optional embedding supplement (Agentless v1.5 combined) -> union (round-robin) with LLM picks
    if embed and len(ranked) < topk:
        emb = _embed_supplement(repo, commit, issue, paths,
                                topk, model_emb or os.environ.get("EMBED_MODEL", "BAAI/bge-m3"))
        ranked = _round_robin(ranked, emb)[:topk]
    # additive graph import-neighbor expansion (recall booster; never drops LLM picks)
    if expand_graph and 0 < len(ranked) < topk:
        try:
            import hybrid_loop_agentic as hla
            srcs = {}
            for f in ranked[:6]:
                try: srcs[f] = p0.fetch_file(repo, commit, f)
                except Exception: pass
            for nb in hla.import_neighbors(srcs, paths):
                if nb in valid and nb not in ranked:
                    ranked.append(nb)
                    if len(ranked) >= topk: break
        except Exception:
            pass
    return ranked[:topk]


if __name__ == "__main__":
    import argparse, sys
    ap = argparse.ArgumentParser()
    ap.add_argument("--iid"); ap.add_argument("--topk", type=int, default=10)
    ap.add_argument("--embed", action="store_true")
    args = ap.parse_args()
    model = os.environ.get("MODEL", "deepseek-ai/DeepSeek-V3")
    rows = {r["instance_id"]: r for r in p0.load_rows(500)}
    r = rows[args.iid]; issue = (r.get("problem_statement") or "")[:5000]
    files = p0.parse_patch(r.get("patch") or ""); gold = [f for f in files if f.endswith(".py")]
    ranked = localize_files(model, r["repo"], r["base_commit"], issue, topk=args.topk, embed=args.embed)
    print("gold files:", gold, file=sys.stderr)
    print("ranked    :", ranked, file=sys.stderr)
    print("file_recall:", round(len([f for f in gold if f in ranked]) / len(gold), 3), file=sys.stderr)
