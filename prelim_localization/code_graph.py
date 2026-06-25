#!/usr/bin/env python3
"""code_graph.py — ARISE-style multi-granularity program graph (pure `ast`).

Borrows ARISE (arXiv:2605.03117, "A Repository-level Graph Representation and Toolset
for Agentic Fault Localization and Program Repair"):

  nodes  {Module, Class, Function, Method, Statement}  with (file, start, end, name)
  edges  structural {Contains, Imports, Calls/CalledBy, Inherits}
         data-flow  {DataflowDefUse, DataflowUseDef}  (statement-level, intra-procedural)

ARISE's ablation shows the **statement-level def-use slice** (Tier-2) is the active
ingredient (+7 Line Recall@1 alone). We reuse it two ways in hybrid_loop:
  (1) STATIC first link — augment the localizer prompt with `skeleton()` + a def-use
      slice, and RANK candidate lines via `rank_suspect_lines()` (= ARISE
      build_context_bundle score α·rel + β·prox + γ·slice). The ranked list is the
      confidence ordering the old P8 union lacked → fixes its Recall@1 loss.
  (2) DYNAMIC loop — each round extract the most-likely candidate gold lines via a
      def-use slice seeded by the issue + the LATEST traceback; execution then
      verifies/narrows them (the user's "图中动态抽候选 gold 行→执行找出正确 gold 行").

Pure stdlib (ast, re, math) — no third-party deps, matching the repo style.

Self-test (no network/Docker):
    python code_graph.py --repo pydata/xarray --commit <sha> --path xarray/core/nanops.py
    python code_graph.py --file some_local.py --issue "..."
"""
from __future__ import annotations
import ast, math, re, sys
from collections import defaultdict

# ----------------------------- tokenization ----------------------------------

_TOK = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

def tokenize(text):
    """Identifier tokens, lowercased, split on camelCase / snake_case, len>=3."""
    out = []
    for m in _TOK.findall(text or ""):
        parts = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", m).replace("_", " ").split()
        for p in parts:
            p = p.lower()
            if len(p) >= 3:
                out.append(p)
        if len(m) >= 3:
            out.append(m.lower())
    return out

# ------------------------------ graph build ----------------------------------

class CodeGraph:
    """Single-file multi-granularity graph. (Repo-level file ranking is done by
    `rank_files`, which builds one lightweight CodeGraph per candidate file.)"""

    def __init__(self, src, path="<file>"):
        self.src = src
        self.path = path
        self.lines = src.splitlines()
        self.nlines = len(self.lines)
        self.ok = True
        # node tables
        self.funcs = []          # [{name,start,end,args,calls(set),class}]
        self.classes = []        # [{name,start,end,bases}]
        self.line_func = {}      # lineno -> func index
        self.line_class = {}     # lineno -> class name
        # def-use (intra-procedural): adjacency over STATEMENT lines
        self.duf = defaultdict(set)   # def_line -> {use_line}   (DataflowDefUse)
        self.dub = defaultdict(set)   # use_line -> {def_line}   (DataflowUseDef)
        self.stmt_line = {}      # any lineno -> enclosing top-level-in-func statement line
        self.stmt_span = {}      # stmt_line -> stmt END line (materialize multi-line statements)
        try:
            self.tree = ast.parse(src)
        except Exception:
            self.tree = None
            self.ok = False
            return
        self._build()

    # -- structural + data-flow passes -------------------------------------
    def _build(self):
        # classes
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):
                end = getattr(node, "end_lineno", node.lineno)
                bases = [self._name(b) for b in node.bases]
                self.classes.append({"name": node.name, "start": node.lineno,
                                     "end": end, "bases": [b for b in bases if b]})
                for ln in range(node.lineno, end + 1):
                    self.line_class[ln] = node.name
        # functions/methods (+ which class encloses them)
        cls_at = {}
        for c in self.classes:
            for ln in range(c["start"], c["end"] + 1):
                cls_at[ln] = c["name"]
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end = getattr(node, "end_lineno", node.lineno)
                fi = len(self.funcs)
                args = [a.arg for a in node.args.args] + [a.arg for a in getattr(node.args, "kwonlyargs", [])]
                calls = set()
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call):
                        nm = self._call_name(sub.func)
                        if nm:
                            calls.add(nm)
                self.funcs.append({"name": node.name, "start": node.lineno, "end": end,
                                   "args": args, "calls": calls, "class": cls_at.get(node.lineno)})
                for ln in range(node.lineno, end + 1):
                    self.line_func[ln] = fi
                self._defuse(node)
        # CalledBy / Calls resolution among in-file functions
        self.name2func = defaultdict(list)
        for i, f in enumerate(self.funcs):
            self.name2func[f["name"]].append(i)

    @staticmethod
    def _name(n):
        if isinstance(n, ast.Name): return n.id
        if isinstance(n, ast.Attribute): return n.attr
        return None

    @staticmethod
    def _call_name(fn):
        if isinstance(fn, ast.Name): return fn.id
        if isinstance(fn, ast.Attribute): return fn.attr
        return None

    def _defuse(self, fnode):
        """Intra-procedural def-use over top-level statements of a function body
        (ARISE: one Statement node per top-level AST statement). For each use of v
        at stmt s, link the last preceding def of v in source order -> s."""
        stmts = list(fnode.body)
        # map every descendant line to its enclosing top-level stmt line
        stmt_of = {}
        for s in stmts:
            s_end = getattr(s, "end_lineno", s.lineno)
            self.stmt_span[s.lineno] = max(self.stmt_span.get(s.lineno, s.lineno), s_end)
            for ln in range(s.lineno, s_end + 1):
                stmt_of[ln] = s.lineno
            self.stmt_line.setdefault(s.lineno, s.lineno)
        for ln, sl in stmt_of.items():
            self.stmt_line[ln] = sl
        # function params are defs at the def-header line
        params = {a.arg for a in fnode.args.args} | {a.arg for a in getattr(fnode.args, "kwonlyargs", [])}
        if getattr(fnode.args, "vararg", None): params.add(fnode.args.vararg.arg)
        if getattr(fnode.args, "kwarg", None): params.add(fnode.args.kwarg.arg)
        last_def = {p: fnode.lineno for p in params}
        # walk statements in order; collect defs/uses per statement
        for s in stmts:
            uses, defs = self._stmt_defs_uses(s)
            sl = s.lineno
            for v in uses:
                if v in last_def and last_def[v] != sl:
                    d = last_def[v]
                    self.duf[d].add(sl)
                    self.dub[sl].add(d)
            for v in defs:
                last_def[v] = sl

    def _stmt_defs_uses(self, s):
        """Vars defined and used within a single top-level statement subtree."""
        uses, defs = set(), set()
        for n in ast.walk(s):
            if isinstance(n, ast.Name):
                if isinstance(n.ctx, ast.Load):
                    uses.add(n.id)
                elif isinstance(n.ctx, (ast.Store, ast.Del)):
                    defs.add(n.id)
            elif isinstance(n, ast.arg):
                defs.add(n.arg)
        # loop / with / comprehension targets are defs (already Name-Store above)
        return uses, defs

    # -- queries -----------------------------------------------------------
    def func_of(self, ln):
        fi = self.line_func.get(ln)
        return self.funcs[fi] if fi is not None else None

    def _stmt_end(self, s):
        """End line of the top-level statement starting at line s (s itself if unknown).
        Lets a def-use slice materialize FULL multi-line statements, not just headers."""
        return self.stmt_span.get(s, s)

    def skeleton(self, max_funcs=60):
        """Compact structural summary for the prompt: classes + functions with line
        spans, args, and in-file callees (Calls edges)."""
        out = []
        for c in self.classes:
            base = f"({', '.join(c['bases'])})" if c["bases"] else ""
            out.append(f"class {c['name']}{base}  [L{c['start']}-{c['end']}]")
        shown = 0
        for f in self.funcs:
            if shown >= max_funcs:
                out.append(f"... (+{len(self.funcs)-shown} more functions)"); break
            loc = f"{f['class']}." if f["class"] else ""
            callees = sorted(c for c in f["calls"] if c in self.name2func)
            ctail = f"  -> calls: {', '.join(callees[:8])}" if callees else ""
            out.append(f"def {loc}{f['name']}({', '.join(f['args'][:6])})  [L{f['start']}-{f['end']}]{ctail}")
            shown += 1
        return "\n".join(out)

    def seed_from_issue(self, issue):
        """Seed STATEMENT lines: bodies of functions/classes whose names appear in
        the issue, and statements mentioning issue identifiers."""
        toks = set(tokenize(issue))
        raw_ids = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", issue or ""))
        seeds = set()
        for f in self.funcs:
            if f["name"] in raw_ids or f["name"].lower() in toks:
                seeds.add(f["start"])
        for c in self.classes:
            if c["name"] in raw_ids:
                seeds.add(c["start"])
        # statements that mention an issue identifier
        for i, ln in enumerate(self.lines, 1):
            if ln.strip().startswith("#"):
                continue
            lid = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", ln))
            if lid & raw_ids and self.line_func.get(i) is not None:
                seeds.add(self.stmt_line.get(i, i))
        return seeds

    def seed_from_traceback(self, failure):
        """Seed lines from a failing-test traceback: line numbers reported in THIS
        file, plus function names it names."""
        seeds = set()
        base = self.path.replace("\\", "/").rsplit("/", 1)[-1]
        for m in re.finditer(r"([A-Za-z0-9_./-]+\.py)[\"']?,?\s*line\s*(\d+)", failure or ""):
            if m.group(1).replace("\\", "/").endswith(base):
                ln = int(m.group(2))
                if 1 <= ln <= self.nlines:
                    seeds.add(self.stmt_line.get(ln, ln))
        # "in <funcname>" frames
        for m in re.finditer(r"in (\w+)\b", failure or ""):
            for fi in self.name2func.get(m.group(1), []):
                seeds.add(self.funcs[fi]["start"])
        return seeds

    def dataflow_slice(self, seeds, direction="both", depth=3, cap=80):
        """BFS over def-use edges from seed statement lines -> related statement
        lines (the candidate set). direction: backward(use->def), forward(def->use)."""
        if not seeds:
            return set()
        frontier = set(self.stmt_line.get(s, s) for s in seeds)
        seen = set(frontier)
        for _ in range(depth):
            nxt = set()
            for ln in frontier:
                if direction in ("forward", "both"):
                    nxt |= self.duf.get(ln, set())
                if direction in ("backward", "both"):
                    nxt |= self.dub.get(ln, set())
            nxt -= seen
            seen |= nxt
            frontier = nxt
            if len(seen) >= cap or not frontier:
                break
        return seen

    def _idf(self):
        """Inverse line-frequency over the file (rare tokens are more discriminative)."""
        df = defaultdict(int)
        toks_per_line = []
        for ln in self.lines:
            t = set(tokenize(ln))
            toks_per_line.append(t)
            for w in t:
                df[w] += 1
        N = max(1, self.nlines)
        idf = {w: math.log(1 + N / c) for w, c in df.items()}
        return idf, toks_per_line

    def _line_scores(self, issue, failure="", coverage_lines=None,
                     alpha=1.0, beta=0.6, gamma=1.2, delta=0.8):
        """{line: score} over executable lines. score = α·rel(issue tf-idf) + β·prox
        (struct proximity to seed funcs) + γ·slice(def-use membership) + δ·covered
        (line executed by the failing test — a traceback-FREE navigation signal)."""
        if not self.ok:
            return {}, set()
        issue_toks = set(tokenize(issue)) | set(tokenize(failure))
        idf, toks_per_line = self._idf()
        cov = set(coverage_lines or [])
        seeds = self.seed_from_issue(issue) | self.seed_from_traceback(failure)
        sl = self.dataflow_slice(seeds, "both")
        seed_funcs = {self.line_func.get(s) for s in seeds if self.line_func.get(s) is not None}
        prox_funcs = set(seed_funcs)
        for fi in list(seed_funcs):
            if fi is None: continue
            for cal in self.funcs[fi]["calls"]:
                prox_funcs |= set(self.name2func.get(cal, []))
        scores = {}
        for i, ln in enumerate(self.lines, 1):
            s = ln.strip()
            if not s or s.startswith("#") or self.line_func.get(i) is None:
                continue
            rel = sum(idf.get(w, 0.0) for w in (toks_per_line[i - 1] & issue_toks))
            fi = self.line_func.get(i)
            prox = 1.0 if fi in seed_funcs else (0.4 if fi in prox_funcs else 0.0)
            inslice = 1.0 if self.stmt_line.get(i, i) in sl else 0.0
            covered = 1.0 if i in cov else 0.0
            sc = alpha * rel + beta * prox + gamma * inslice + delta * covered
            if sc > 0:
                scores[i] = sc
        return scores, cov

    def rank_suspect_lines(self, issue, failure="", topn=15, coverage_lines=None):
        """RANKED executable line numbers (most→least suspicious)."""
        scores, _ = self._line_scores(issue, failure, coverage_lines)
        return sorted(scores, key=lambda k: (-scores[k], k))[:topn]

    def dataflow_slice_dist(self, seeds, depth=3, cap=120):
        """Like dataflow_slice but returns {stmt_line: min BFS hop-distance from a seed}
        (0 = seed). Enables a GRADED slice term — ARISE uses the def-use slice as a graded
        ranking signal, not a binary membership flag (adversarial-review fix)."""
        if not seeds:
            return {}
        frontier = set(self.stmt_line.get(s, s) for s in seeds)
        dist = {ln: 0 for ln in frontier}
        for d in range(1, depth + 1):
            nxt = set()
            for ln in frontier:
                nxt |= self.duf.get(ln, set()) | self.dub.get(ln, set())
            nxt = {ln for ln in nxt if ln not in dist}
            for ln in nxt:
                dist[ln] = d
            frontier = nxt
            if len(dist) >= cap or not frontier:
                break
        return dist

    def line_scores_v2(self, issue, failure="", coverage_lines=None, *, graded=True,
                       use_coverage=True, alpha=1.0, beta=0.6, gamma=1.2, delta=0.8, decay=0.6):
        """Head-to-head scoring (does NOT touch production `_line_scores`, so hybrid_loop
        and the shipped V0 are byte-unchanged). Two knobs the adversarial review demanded:
          graded       : GRADED def-use slice term gamma*decay**hops (the steelmanned ARISE
                         signal) instead of a binary 0/1 in-slice flag.
          use_coverage : explicit toggle so a 'pure STATIC' ARISE ranker provably EXCLUDES
                         the failing-test coverage term (delta*covered), which otherwise
                         lives inside the score and would contaminate the V0-vs-ARISE axis."""
        if not self.ok:
            return {}
        issue_toks = set(tokenize(issue)) | set(tokenize(failure))
        idf, toks_per_line = self._idf()
        cov = set(coverage_lines or []) if use_coverage else set()
        seeds = self.seed_from_issue(issue) | self.seed_from_traceback(failure)
        sl_dist = self.dataflow_slice_dist(seeds) if graded else \
                  {ln: 0 for ln in self.dataflow_slice(seeds, "both")}
        seed_funcs = {self.line_func.get(s) for s in seeds if self.line_func.get(s) is not None}
        prox_funcs = set(seed_funcs)
        for fi in list(seed_funcs):
            if fi is None: continue
            for cal in self.funcs[fi]["calls"]:
                prox_funcs |= set(self.name2func.get(cal, []))
        scores = {}
        for i, ln in enumerate(self.lines, 1):
            s = ln.strip()
            if not s or s.startswith("#") or self.line_func.get(i) is None:
                continue
            rel = sum(idf.get(w, 0.0) for w in (toks_per_line[i - 1] & issue_toks))
            fi = self.line_func.get(i)
            prox = 1.0 if fi in seed_funcs else (0.4 if fi in prox_funcs else 0.0)
            stmt = self.stmt_line.get(i, i)
            inslice = (decay ** sl_dist[stmt]) if stmt in sl_dist else 0.0
            covered = 1.0 if i in cov else 0.0
            sc = alpha * rel + beta * prox + gamma * inslice + delta * covered
            if sc > 0:
                scores[i] = sc
        return scores

    def rank_functions(self, issue, failure="", coverage_lines=None, topn=6):
        """RANKED functions (for REGION-based editing of large files): aggregate line
        suspiciousness per function + boosts for (a) function executed by the failing
        test, (b) function name = an issue symbol. Returns [{name,start,end,score}]."""
        if not self.ok or not self.funcs:
            return []
        scores, cov = self._line_scores(issue, failure, coverage_lines)
        raw_ids = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", issue or ""))
        fscore = []
        for f in self.funcs:
            body = range(f["start"], f["end"] + 1)
            s = sum(scores.get(ln, 0.0) for ln in body)
            if cov and (set(body) & cov): s += 1.5           # executed by failing test
            if f["name"] in raw_ids: s += 2.0                # named in the issue
            fscore.append((s, f))
        fscore.sort(key=lambda x: (-x[0], x[1]["start"]))
        return [{"name": f["name"], "start": f["start"], "end": f["end"], "score": round(s, 2)}
                for s, f in fscore[:topn] if s > 0] or \
               [{"name": f["name"], "start": f["start"], "end": f["end"], "score": 0.0}
                for f in self.funcs[:topn]]


# --------------------- repo-level file ranking (Exp 2) -----------------------

def rank_files(issue, file_srcs, topn=10):
    """Re-rank candidate files by issue relevance + structure. `file_srcs` is
    {path: source}. Score = TF-IDF of issue tokens over each file's ENTITY names
    (class/function/module) + a boost for files that define an issue symbol. Cheap:
    parses only the (already narrowed) candidate set, never the whole repo."""
    issue_toks = set(tokenize(issue))
    raw_ids = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", issue or ""))
    ent_tokens, defines_symbol = {}, {}
    df = defaultdict(int)
    for path, src in file_srcs.items():
        g = CodeGraph(src, path)
        names = [f["name"] for f in g.funcs] + [c["name"] for c in g.classes]
        names.append(path.replace("\\", "/").rsplit("/", 1)[-1][:-3])  # module name
        toks = set()
        for nm in names:
            toks |= set(tokenize(nm))
        ent_tokens[path] = toks
        defines_symbol[path] = bool(set(names) & raw_ids)
        for w in toks:
            df[w] += 1
    N = max(1, len(file_srcs))
    idf = {w: math.log(1 + N / c) for w, c in df.items()}
    scores = {}
    for path, toks in ent_tokens.items():
        rel = sum(idf.get(w, 0.0) for w in (toks & issue_toks))
        scores[path] = rel + (2.0 if defines_symbol[path] else 0.0)
    return sorted(scores, key=lambda k: (-scores[k], k))[:topn]


# --------------------------------- self-test ---------------------------------

def main():
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo"); ap.add_argument("--commit"); ap.add_argument("--path")
    ap.add_argument("--file"); ap.add_argument("--issue", default="")
    ap.add_argument("--failure", default="")
    args = ap.parse_args()
    if args.file:
        src = open(args.file, encoding="utf-8", errors="replace").read()
        path = args.file
    else:
        import p0_line_recall as p0
        src = p0.fetch_file(args.repo, args.commit, args.path)
        path = args.path
    g = CodeGraph(src, path)
    print(f"ok={g.ok}  funcs={len(g.funcs)} classes={len(g.classes)} "
          f"defuse_edges={sum(len(v) for v in g.duf.values())}")
    print("\n--- skeleton ---\n" + g.skeleton(max_funcs=20))
    if args.issue or args.failure:
        seeds = g.seed_from_issue(args.issue) | g.seed_from_traceback(args.failure)
        print(f"\nseeds={sorted(seeds)[:20]}")
        print(f"slice={sorted(g.dataflow_slice(seeds))[:30]}")
        print(f"ranked_suspect_lines(top15)={g.rank_suspect_lines(args.issue, args.failure)}")

if __name__ == "__main__":
    main()
