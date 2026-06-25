#!/usr/bin/env python3
"""arise_file_loc — ARISE-style AGENTIC file localization (the reference file-finder, rebuilt).

Replaces the single-shot Agentless front-end (file_localize.localize_files) with ARISE's recipe so
the us-vs-ARISE comparison is 口径-unified on file-loc and ONLY the line-loc differs (our dynamic
region-recall + coverage). ARISE (arXiv:2605.03117) navigates a repository-level multi-granularity
PROGRAM GRAPH through a tiered TOOL API with a SWE-agent loop; file R@1=67 / R@3=82 on SWE-bench Lite
with Qwen2.5-Coder-32B (the same backbone as us).

What this module builds:
  (1) RepoIndex — a repo-level graph over a real local checkout (repo_snapshot tarball, no Docker):
        nodes   {Module(file), Class, Function/Method}  with (file, start, end, name, qualname)
        edges   Contains (file->entities), Imports (file->file, + reverse Importers)
        Calls   served on-demand via ripgrep (search_code), the cheap faithful proxy for CalledBy.
  (2) A tiered TOOL API the agent calls one-at-a-time:
        search_code / search_entity / get_skeleton / get_imports / get_importers / read_lines
  (3) An agentic ReAct loop: the LLM reasons over the graph via the tools and emits a RANKED file
      answer. Recall-safe: validates paths against the real tree; falls back to the files it actually
      surfaced during exploration (frequency-ranked) if it never commits a clean answer.

Drop-in: localize_files_arise(model, repo, commit, issue, topk=10) -> ranked repo-relative .py paths,
same signature/return as file_localize.localize_files, so egl_e2e can switch front-ends with a flag.

    OPENAI_BASE_URL=... MODEL=Qwen2.5-Coder-32B python arise_file_loc.py --iid <instance_id>
"""
from __future__ import annotations
import argparse, ast, json, os, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import p0_line_recall as p0
import code_graph as cg
import repo_snapshot as rs
from hybrid_loop import _llm

HERE = Path(__file__).resolve().parent
_INDEX_CACHE = {}                      # str(root) -> RepoIndex (one build per repo@commit per process)


def _module_name(relpath):
    """repo-relative .py path -> dotted module name (a/b/c.py -> a.b.c ; a/b/__init__.py -> a.b)."""
    p = relpath[:-3].replace("\\", "/")
    if p.endswith("/__init__"):
        p = p[:-9]
    return p.replace("/", ".")


class RepoIndex:
    """Repo-level program graph built once from a local checkout (Contains + Imports edges + an
    entity name index). Calls/CalledBy are answered on demand by ripgrep (search_code)."""

    def __init__(self, root):
        self.root = Path(root)
        self.paths = []                                  # repo-relative .py paths
        self.entities = []                               # {kind,name,qualname,file,start,end}
        self.name_index = defaultdict(list)              # name -> [entity]
        self.imports = defaultdict(set)                  # file -> {imported repo file}
        self.importers = defaultdict(set)                # file -> {file that imports it}
        self._skel = {}                                  # file -> skeleton text (lazy)
        self._build()

    def _build(self):
        mod2file = {}
        raw_imports = {}                                 # file -> {dotted module strings}
        for fp in self.root.rglob("*.py"):
            rel = str(fp.relative_to(self.root)).replace("\\", "/")
            self.paths.append(rel)
            mod2file[_module_name(rel)] = rel
            try:
                src = fp.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(src)
            except Exception:
                continue
            nlines = src.count("\n") + 1
            self._add(rel, "file", _module_name(rel).rsplit(".", 1)[-1], rel, 1, nlines)
            cls_at = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    end = getattr(node, "end_lineno", node.lineno)
                    for ln in range(node.lineno, end + 1):
                        cls_at[ln] = node.name
                    self._add(rel, "class", node.name, f"{rel}::{node.name}", node.lineno, end)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    end = getattr(node, "end_lineno", node.lineno)
                    cls = cls_at.get(node.lineno)
                    qual = f"{rel}::{cls}.{node.name}" if cls else f"{rel}::{node.name}"
                    self._add(rel, "method" if cls else "function", node.name, qual, node.lineno, end)
            pkg = rel[:-3].replace("\\", "/").split("/")[:-1]    # package (dir) of this module
            mods = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for a in node.names:
                        mods.add(a.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.level:                               # relative import -> resolve to absolute
                        base = pkg[:len(pkg) - (node.level - 1)] if node.level - 1 <= len(pkg) else []
                        prefix = ".".join(base)
                        full = (prefix + "." + node.module) if (prefix and node.module) else (node.module or prefix)
                    else:
                        full = node.module
                    if full:
                        mods.add(full)
                        for a in node.names:
                            mods.add(full + "." + a.name)
            raw_imports[rel] = mods
        # resolve Imports edges (dotted module -> repo file, longest match wins) + reverse Importers
        for rel, mods in raw_imports.items():
            for m in mods:
                tgt = mod2file.get(m)
                if not tgt:                              # try trimming trailing attr (from x import y)
                    tgt = mod2file.get(m.rsplit(".", 1)[0]) if "." in m else None
                if tgt and tgt != rel:
                    self.imports[rel].add(tgt)
                    self.importers[tgt].add(rel)

    def _add(self, file, kind, name, qual, start, end):
        e = {"kind": kind, "name": name, "qualname": qual, "file": file, "start": start, "end": end}
        self.entities.append(e)
        self.name_index[name].append(e)

    # -- tools --------------------------------------------------------------
    def search_code(self, query, max_results=25):
        try:
            hits = rs.rg_search(self.root, query, max_results=max_results)
        except Exception as e:
            return f"(search error: {repr(e)[:80]})", []
        if not hits:
            return "(no matches)", []
        files = []
        lines = []
        for rel, ln, txt in hits:
            files.append(rel)
            lines.append(f"{rel}:{ln}: {txt.strip()[:160]}")
        return "\n".join(lines), files

    def search_entity(self, name, max_results=25):
        hits = self.name_index.get(name, [])
        if not hits:                                     # case-insensitive / substring fallback
            low = name.lower()
            hits = [e for e in self.entities if low in e["name"].lower()][:max_results]
        if not hits:
            return "(no entity named %r)" % name, []
        out = [f"{e['kind']} {e['qualname']}  [L{e['start']}-{e['end']}]" for e in hits[:max_results]]
        return "\n".join(out), [e["file"] for e in hits[:max_results]]

    def get_skeleton(self, path):
        path = self._resolve(path)
        if not path:
            return "(file not found)", []
        if path not in self._skel:
            try:
                src = (self.root / path).read_text(encoding="utf-8", errors="replace")
                g = cg.CodeGraph(src, path)
                self._skel[path] = g.skeleton(max_funcs=40) if g.ok else "(unparseable)"
            except Exception as e:
                self._skel[path] = f"(read error: {repr(e)[:60]})"
        return f"### {path}\n{self._skel[path][:1800]}", [path]

    def get_imports(self, path):
        path = self._resolve(path)
        if not path:
            return "(file not found)", []
        tgt = sorted(self.imports.get(path, set()))
        return ("imports: " + (", ".join(tgt) if tgt else "(none in-repo)")), tgt

    def get_importers(self, path):
        path = self._resolve(path)
        if not path:
            return "(file not found)", []
        src = sorted(self.importers.get(path, set()))
        return ("imported by: " + (", ".join(src[:30]) if src else "(none in-repo)")), src

    def read_lines(self, path, start=1, end=None):
        path = self._resolve(path)
        if not path:
            return "(file not found)", []
        try:
            lines = (self.root / path).read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception as e:
            return f"(read error: {repr(e)[:60]})", []
        start = max(1, int(start)); end = min(len(lines), int(end) if end else start + 40)
        body = "\n".join(f"{i}: {lines[i-1]}" for i in range(start, end + 1))
        return f"### {path} [L{start}-{end}]\n{body[:1800]}", [path]

    def _resolve(self, path):
        """Tolerant path resolution: exact, else unique suffix match against the real tree."""
        if not path:
            return None
        path = path.strip().replace("\\", "/").lstrip("./")
        if path in self.paths:
            return path
        m = [p for p in self.paths if p.endswith("/" + path) or p == path]
        return m[0] if len(m) == 1 else None

    def validate(self, paths):
        """Map LLM-named paths to real repo paths (recall-safe; drops hallucinations)."""
        out = []
        for p in paths:
            r = self._resolve(p)
            if r and r not in out:
                out.append(r)
        return out


def get_index(repo, commit):
    root = rs.snapshot(repo, commit)
    key = str(root)
    if key not in _INDEX_CACHE:
        _INDEX_CACHE[key] = RepoIndex(root)
    return _INDEX_CACHE[key]


SYSTEM = """You are an expert software engineer performing FILE-LEVEL fault localization. Given a GitHub issue and a repository you explore via TOOLS, identify the repository file(s) that must be EDITED to resolve the issue.

## GitHub issue
{issue}

## Tools — call EXACTLY ONE per step
- search_code{{"query": "<regex/text>"}}: search the repo's Python files; returns matching file:line: text. Use issue keywords, error strings, symbol/class/function names.
- search_entity{{"name": "<ClassOrFuncName>"}}: locate classes/functions/methods by name; returns their file + line span.
- get_skeleton{{"path": "<repo/rel/path.py>"}}: list a file's classes/functions with line spans.
- get_imports{{"path": "<path.py>"}}: in-repo files this file imports.
- get_importers{{"path": "<path.py>"}}: in-repo files that import this file.
- read_lines{{"path": "<path.py>", "start": <int>, "end": <int>}}: read a source snippet.

## Protocol
Output EXACTLY ONE JSON object per step and NOTHING else (no markdown fences):
  to use a tool:  {{"thought": "<brief>", "tool": "search_code", "args": {{"query": "..."}}}}
  to finish:      {{"thought": "<brief>", "answer": ["most_likely.py", "next.py", ...]}}
Explore until you can name the edit location(s). Then finish with `answer` = a RANKED list (most-likely first) of up to {topk} EXACT repo-relative file paths to edit. Prefer source files over tests. JSON only."""

_TOOLS = {"search_code", "search_entity", "get_skeleton", "get_imports", "get_importers", "read_lines"}


def _extract_json(text):
    """First balanced {...} object in the model output."""
    s = text.find("{")
    while s != -1:
        depth = 0; instr = False; esc = False
        for i in range(s, len(text)):
            c = text[i]
            if instr:
                if esc: esc = False
                elif c == "\\": esc = True
                elif c == '"': instr = False
            else:
                if c == '"': instr = True
                elif c == "{": depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[s:i + 1])
                        except Exception:
                            break
        s = text.find("{", s + 1)
    return None


def _is_test(p):
    pl = p.lower()
    base = pl.rsplit("/", 1)[-1]
    return "/tests/" in pl or "/test/" in pl or base.startswith("test_") or base.endswith("_test.py") or "conftest" in base


def _demote_tests(paths):
    """SWE-bench edit targets are essentially never test files (tests live in the test_patch) -> stable-sort
    non-test files ahead of test files so a stray test can't squat rank #1."""
    return [p for p in paths if not _is_test(p)] + [p for p in paths if _is_test(p)]


def localize_files_arise(model, repo, commit, issue, topk=10, max_turns=12, verbose=False, stats=None):
    """ARISE-style agentic file localization. Returns up to `topk` ranked repo-relative .py paths.
    If `stats` (a dict) is given, records {turns, committed, n_seen} for cost/behavior analysis."""
    idx = get_index(repo, commit)
    if not idx.paths:
        return []
    seen = Counter()                                     # files surfaced by tools (recall-safe fallback)
    log = []                                             # (step_json_str, observation)
    act_count = {}                                       # repeated-call detector (the agent loops on read_lines)
    task = SYSTEM.format(issue=issue[:5000], topk=topk)
    answer = None
    for turn in range(max_turns):
        push = turn >= max_turns - 2                      # last 2 turns: demand a decision
        convo = task + "\n\n## Exploration log\n"
        for j, (act, obs) in enumerate(log[-8:], 1):     # keep the last 8 steps to bound prompt size
            convo += f"[step {j}] you: {act}\n[step {j}] result:\n{obs[:1100]}\n\n"
        convo += ("You now have enough to decide. Output your FINAL `answer` JSON (ranked paths, SOURCE files before tests)."
                  if push else "Now output your next JSON (a tool call, or your final `answer`).")
        try:
            raw = _llm(model, convo, timeout=120, retries=2)
        except Exception:
            break
        obj = _extract_json(raw)
        if obj is None:
            log.append(('(unparsed)', "Output ONE JSON object only.")); continue
        if "answer" in obj and isinstance(obj["answer"], list):
            answer = [str(x) for x in obj["answer"]]
            break
        tool = obj.get("tool"); args = obj.get("args") or {}
        act = json.dumps({k: obj.get(k) for k in ("tool", "args") if k in obj}, ensure_ascii=False)[:300]
        if tool not in _TOOLS:
            log.append((act, f"Unknown tool {tool!r}. Valid tools: {sorted(_TOOLS)}.")); continue
        act_count[act] = act_count.get(act, 0) + 1
        if act_count[act] >= 2:                           # break the read-the-same-thing loop
            log.append((act, "You ALREADY ran this exact call (its result is above). Do NOT repeat it — "
                             "explore something NEW, or output your final `answer` now.")); continue
        try:
            obs, files = getattr(idx, tool)(**args)
        except TypeError as e:
            obs, files = f"(bad args for {tool}: {repr(e)[:80]})", []
        except Exception as e:
            obs, files = f"(tool error: {repr(e)[:80]})", []
        for f in files:
            seen[f] += 1
        log.append((act, obs))
        if verbose:
            print(f"  [turn {turn+1}] {act} -> {len(files)} files", file=sys.stderr)
    # forced final answer if the agent never committed (better than a blind frequency fallback)
    if answer is None and log:
        convo = task + "\n\n## Exploration log\n" + "".join(
            f"[step {j}] you: {a}\n[step {j}] result:\n{o[:900]}\n\n" for j, (a, o) in enumerate(log[-8:], 1))
        convo += (f"EXPLORATION ENDED. Output ONLY your final `answer` JSON now: up to {topk} repo-relative "
                  "file paths to edit, MOST-LIKELY FIRST, SOURCE files before tests.")
        try:
            obj = _extract_json(_llm(model, convo, timeout=120, retries=2))
            if obj and isinstance(obj.get("answer"), list):
                answer = [str(x) for x in obj["answer"]]
        except Exception:
            pass
    if stats is not None:
        stats["turns"] = len(log); stats["committed"] = answer is not None; stats["n_seen"] = len(seen)
    # finalize: validated agent answer first, then recall-safe fallback by exploration frequency; demote tests
    ranked = idx.validate(answer) if answer else []
    if len(ranked) < topk:
        for f, _ in seen.most_common():
            if f not in ranked:
                ranked.append(f)
            if len(ranked) >= topk:
                break
    return _demote_tests(ranked)[:topk]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iid")
    ap.add_argument("--topk", type=int, default=10)
    ap.add_argument("--max-turns", type=int, default=12)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    model = os.environ.get("MODEL", "Qwen2.5-Coder-32B")
    rows = {r["instance_id"]: r for r in p0.load_rows(500)}
    r = rows[args.iid]
    issue = (r.get("problem_statement") or "")[:5000]
    files = p0.parse_patch(r.get("patch") or ""); gold = [f for f in files if f.endswith(".py")]
    ranked = localize_files_arise(model, r["repo"], r["base_commit"], issue,
                                  topk=args.topk, max_turns=args.max_turns, verbose=args.verbose)
    print("gold files :", gold, file=sys.stderr)
    print("ranked     :", ranked, file=sys.stderr)
    hit1 = int(bool(ranked[:1]) and ranked[0] in gold)
    print(f"file_recall: {round(len([f for f in gold if f in ranked]) / len(gold), 3)}  R@1={hit1}", file=sys.stderr)


if __name__ == "__main__":
    main()
