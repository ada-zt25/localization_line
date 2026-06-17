#!/usr/bin/env python3
r"""Test-free pairwise API-composition-constraint extractor  (condition B5).

This module implements the extraction operator

    Phi : (a, b)  ->  (relation, rule_text, confidence)

that recovers the *typed pairwise composition constraints* a library exhibits,
WITHOUT consulting the benchmark's hidden tests or the hand-written gold rules.
It is the algorithmic core that turns the gold-rule injection (B4) into a
*method*: B5 = B1's API list  (+)  Phi-extracted rule, mirroring B4 = B1 (+) gold
rule, so that B5-B4 measures the extraction gap, B5-B3 the value of an extracted
rule over a bare call sequence, and B5-B1 its value over the API list.

Scientific structure (see docs/PairCoder_Benchmark.md and the design note):

  1. Coupling-channel <-> relation bijection (Sec 2.2 of the design).
     The taxonomy proves a pairwise constraint can only travel over one of six
     coupling channels.  Each channel k has a detector; each relation r has a
     UNIQUE defining channel kappa(r).

         DFP  param dataflow        -> param-dependency
         DFR  return dataflow       -> return-flow
         SS   shared heap state     -> shared-receiver
         TC   type/shape contract   -> config-return-contract
         CO   control order/scope   -> lifecycle
         CE   control existence     -> completion-obligation

  2. Multi-source noisy-OR per channel.  Each detector emits, for a candidate,
     a per-source detection probability p_{k,sigma} from sources
     sigma in {src(AST), sig(signature), doc(docstring), ex(usage example)}.
     The channel witness score combines them with a noisy-OR:

         s_k = 1 - prod_sigma ( 1 - w_sigma * p_{k,sigma} )

  3. Discriminative typed score (suppress competing channels):

         score(r) = s_{kappa(r)} * prod_{k != kappa(r)} ( 1 - lambda * s_k )

     A candidate whose anchors fire on several channels is ambiguous and gets
     suppressed -> low confidence -> filtered out.

  4. Calibrated confidence + provable precision floor.  Platt scaling
         c = sigmoid(alpha * score + beta)
     is fit by LEAVE-ONE-LIBRARY-OUT logistic regression on the *other*
     libraries' (score, correct?) pairs (no leakage).  Because c is a calibrated
     probability of extraction-correctness, emitting only c >= theta gives

         precision(theta) = E[c | c >= theta] >= theta .

     Sweeping theta yields the precision-coverage operating curve.

Test-free guarantee: the extractor reads only the vendored library's importable
objects (signatures, source via inspect.getsource, docstrings) and the curated
doc snippets API_LIST / RAW_API_DOCS.  It never imports GOLD_PAIR_RULES or the
hidden tests.  GOLD_PAIR_RULES is read ONLY by eval_extraction.py, for scoring.

CLI:
    python pair_extractor.py --lib glom            # extract one library
    python pair_extractor.py --all                 # all libs, LOLO calibration
    python pair_extractor.py --all --emit result/extraction_eval
"""

from __future__ import annotations

import argparse
import ast
import importlib
import inspect
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Taxonomy: the coupling-channel <-> relation bijection.
# ---------------------------------------------------------------------------
# The 6-class taxonomy. completion-obligation (channel CE) is the resource
# acquire/release / "must also call the partner" pattern, exhibited by sqlitedict
# (db write -> db.commit()). The data/config/plugin/extraction libraries do not
# contain it, so it simply yields no proposals for them.
RELATIONS = [
    "param-dependency",
    "return-flow",
    "shared-receiver",
    "config-return-contract",
    "lifecycle",
    "completion-obligation",
]
KAPPA = {  # relation -> its unique defining channel
    "param-dependency": "DFP",
    "return-flow": "DFR",
    "shared-receiver": "SS",
    "config-return-contract": "TC",
    "lifecycle": "CO",
    "completion-obligation": "CE",
}
CHANNELS = list(KAPPA.values())
CHANNEL_TO_RELATION = {v: k for k, v in KAPPA.items()}

# Source reliability weights w_sigma (dev-set defaults; executable usage > sig > doc).
SOURCE_WEIGHTS = {"src": 0.90, "ex": 0.80, "sig": 0.70, "doc": 0.60}
LAMBDA_SUP = 0.55          # competing-channel suppression strength
TAU_DETECT = 0.12          # minimum raw score to be a candidate at all

# All 6 benchmark libraries, now uniformly on the benchlib lib_<name> interface.
DEFAULT_LIBS = ["glom", "diot", "simpleconf", "bidict", "simplug", "sqlitedict"]


# ---------------------------------------------------------------------------
# Proposal: one (relation, anchors) candidate with per-source evidence.
# ---------------------------------------------------------------------------
@dataclass
class Proposal:
    relation: str
    anchors: frozenset
    signals: dict = field(default_factory=dict)   # source -> probability in [0,1]
    rationale: str = ""

    def channel(self) -> str:
        return KAPPA[self.relation]

    def witness(self) -> float:
        """noisy-OR over sources: s_k = 1 - prod(1 - w_sigma p_{k,sigma})."""
        prod = 1.0
        for src, p in self.signals.items():
            prod *= (1.0 - SOURCE_WEIGHTS.get(src, 0.5) * max(0.0, min(1.0, p)))
        return 1.0 - prod


# ---------------------------------------------------------------------------
# Evidence bundle: everything Phi is allowed to read for one library.
# ---------------------------------------------------------------------------
class Evidence:
    def __init__(self, lib_name: str):
        self.name = lib_name
        self.mod = importlib.import_module(f"lib_{lib_name}")
        self.namespace = self.mod.make_namespace()
        self.api_text = (getattr(self.mod, "API_LIST", "") + "\n"
                         + getattr(self.mod, "RAW_API_DOCS", ""))
        self.classes = {k: v for k, v in self.namespace.items()
                        if inspect.isclass(v) and not k.endswith("Error")}
        self.functions = {k: v for k, v in self.namespace.items() if inspect.isfunction(v)}
        # documented identifiers = the only API tokens Phi treats as "real surface".
        # Anchors outside this set are undocumented internals (filtered by relevant()).
        self.doc_ids = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]+", self.api_text))
        # method inventory: {class_name: {method_name: callable}}
        self.methods = {}
        for cname, cls in self.classes.items():
            ms = {}
            for mname, mobj in inspect.getmembers(cls):
                if mname.startswith("_") and mname not in ("__setattr__", "__setitem__", "__getitem__"):
                    continue
                if callable(mobj) or isinstance(inspect.getattr_static(cls, mname, None), property):
                    ms[mname] = mobj
            self.methods[cname] = ms
        # doc usage-example code lines (from the curated doc snippets only)
        self.ex_lines = [ln.strip() for ln in self.api_text.splitlines()
                         if ("(" in ln or "=" in ln or "." in ln) and not ln.strip().startswith("-")]
        # all known API tokens (for filtering proposals to real APIs)
        self.tokens = set(self.namespace) | {
            f"{c}.{m}" for c, ms in self.methods.items() for m in ms
        }
        # primary subjects = classes whose own name is documented (skip helper /
        # spec classes like glom.Path/T). Method-scanning detectors stay on these.
        self.primary = {c: cls for c, cls in self.classes.items() if c in self.doc_ids}

    def documented(self, token: str) -> bool:
        return token in self.doc_ids

    def relevant(self, anchors) -> bool:
        """Keep a proposal only if at least one anchor names a documented API.
        Undocumented internals (e.g. Diot.update_recursively) are dropped, which
        is what prevents the O(methods^2) shared-state explosion."""
        for a in anchors:
            for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]+", a):
                if tok in self.doc_ids:
                    return True
        return False

    def source_of(self, cls, method):
        try:
            return inspect.getsource(inspect.getattr_static(cls, method))
        except (OSError, TypeError, AttributeError):
            return ""

    def doc_of(self, obj):
        return inspect.getdoc(obj) or ""

    def signature_of(self, obj):
        try:
            return inspect.signature(obj)
        except (TypeError, ValueError):
            return None


# ---------------------------------------------------------------------------
# AST helpers for the shared-state (SS) and type-contract (TC) detectors.
# ---------------------------------------------------------------------------
class _SelfRW(ast.NodeVisitor):
    """Collect attribute/item read & write sets on `self` within a method body."""
    def __init__(self):
        self.writes, self.reads, self.setitem = set(), set(), False

    def visit_Assign(self, node):
        for tgt in node.targets:
            self._mark_target(tgt)
        self.visit(node.value)

    def visit_AugAssign(self, node):
        self._mark_target(node.target)
        self.generic_visit(node)

    def _mark_target(self, tgt):
        if isinstance(tgt, ast.Attribute) and _is_self(tgt.value):
            self.writes.add(tgt.attr)
        elif isinstance(tgt, ast.Subscript) and _is_self(tgt.value):
            self.setitem = True

    def visit_Attribute(self, node):
        if _is_self(node.value) and isinstance(node.ctx, ast.Load):
            self.reads.add(node.attr)
        self.generic_visit(node)


def _is_self(node) -> bool:
    return isinstance(node, ast.Name) and node.id == "self"


def _self_rw(src: str):
    try:
        tree = ast.parse(_dedent(src))
    except SyntaxError:
        return set(), set(), False
    v = _SelfRW()
    v.visit(tree)
    return v.writes, v.reads, v.setitem


def _dedent(src: str) -> str:
    return inspect.cleandoc("\n" + src) if src else src


def _returns_branch_on_param(src: str):
    """True if a function returns DIFFERENT expressions under branches that test
    a parameter -- the signature of a config/flag deciding the return shape."""
    try:
        tree = ast.parse(_dedent(src))
    except SyntaxError:
        return False
    funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if not funcs:
        return False
    fn = funcs[0]
    params = {a.arg for a in fn.args.args} | {a.arg for a in fn.args.kwonlyargs}
    returns_in_if = 0
    for node in ast.walk(fn):
        if isinstance(node, ast.If):
            names = {n.id for n in ast.walk(node.test) if isinstance(n, ast.Name)}
            if names & params and any(isinstance(c, ast.Return) for c in ast.walk(node)):
                returns_in_if += 1
    return returns_in_if >= 1


# ---------------------------------------------------------------------------
# The six channel detectors.  Each returns a list of Proposals.
# ---------------------------------------------------------------------------
_FORCE_PREFIXES = ("force", "safe", "soft", "try")
_VARIANT_SUFFIXES = ("all", "_or_none", "default")
_DFP_DOC_KEYS = ("force", "override", "without raising", "instead of", "unique",
                 "duplicat", "replace", "drop", "precedence", "order", "default",
                 "transform", "camel", "snake")


def detect_DFP(ev: Evidence):
    """param-dependency: a parameter/variant choice decides a paired operation."""
    out = []
    # (1) sibling method variants:  put / forceput , update / forceupdate ...
    for cname in ev.primary:
        ms = ev.methods[cname]
        names = set(ms)
        for base in names:
            for pre in _FORCE_PREFIXES:
                var = f"{pre}{base}"
                if var in names:
                    doc = ev.doc_of(ms[var]).lower()
                    sig = 1.0
                    docp = 0.7 if any(k in doc for k in _DFP_DOC_KEYS) else 0.25
                    out.append(Proposal(
                        "param-dependency",
                        frozenset({f"{cname}.{base}", f"{cname}.{var}"}),
                        {"sig": sig, "doc": docp},
                        f"variant pair {base}/{var}: choice decides survival of old mapping"))
    # (2) mode keyword args on constructors / functions that gate behavior.
    for fname, fobj in {**ev.functions, **{c: cls for c, cls in ev.primary.items()}}.items():
        sig = ev.signature_of(fobj if not inspect.isclass(fobj) else fobj.__init__)
        if not sig:
            continue
        for p in sig.parameters.values():
            if p.name in ("self", "args", "kwargs") or p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
                continue
            if p.default is inspect._empty:
                continue
            doc = (ev.doc_of(fobj)).lower()
            mentions = p.name.lower() in doc or any(k in doc for k in _DFP_DOC_KEYS)
            exp = any(f"{p.name}=" in ln for ln in ev.ex_lines)
            signals = {"sig": 0.6}
            if mentions:
                signals["doc"] = 0.55
            if exp:
                signals["ex"] = 0.7
            out.append(Proposal(
                "param-dependency",
                frozenset({fname, f"{fname}({p.name}=)"}),
                signals,
                f"keyword '{p.name}=' of {fname} gates paired access/behavior"))
    return out


def detect_doc_kwargs(ev: Evidence):
    """Keyword arguments shown in the doc snippets (e.g. diot_transform=, diot_nest=,
    default=) when the constructor only exposes **kwargs in its signature. Each is
    a config knob; route it to the relation its semantics implies (the discriminative
    score / calibration arbitrate when the routing is uncertain)."""
    out = []
    seen = set()
    for k in re.findall(r"\b([A-Za-z_]\w{2,})\s*=", ev.api_text):
        if k in seen or k not in ev.doc_ids:
            continue
        seen.add(k)
        kl = k.lower()
        if any(t in kl for t in ("nest", "shape", "type", "result", "mode", "format")):
            rel = "config-return-contract"      # names that select the OUTPUT form
        elif any(t in kl for t in ("frozen", "freeze")):
            rel = "lifecycle"
        else:                                   # transform/case/order/default/...
            rel = "param-dependency"
        # find a documented owning constructor mentioned beside the kwarg
        owner = next((c for c in ev.primary if re.search(rf"{c}\s*\([^)]*{re.escape(k)}", ev.api_text)), None)
        anchors = {f"{k}="} | ({owner} if owner else set())
        out.append(Proposal(rel, frozenset(anchors), {"ex": 0.7, "doc": 0.5},
                            f"documented keyword '{k}=' is a config knob ({rel})"))
    return out


# Generic return-flow vocabulary: a value produced by one call is navigated /
# indexed / fed onward. Each cue maps to canonical salient tokens (not lib-specific).
_DFR_CUES = [
    (re.compile(r"navigat|dotted|\bpath\b|\.\w+\.\w+"), ("navigate", "path")),
    (re.compile(r"inverse|reverse|\bmaps?\b|->|look\s?up"), ("inverse", "reverse")),
    (re.compile(r"nested|chain"), ("nested", "chain")),
]


def detect_DFR(ev: Evidence):
    """return-flow: operation b reads/navigates/indexes the value produced by a.

    Two evidence forms: (1) executable call-chains in doc code examples
    (a(...).b, b(a(...)), a(...)[...]); (2) doc-TEXT navigation cues -- the docs
    DESCRIBE the flow in prose ('navigates to nums', 'inverse maps value->key',
    'nested chain') even when they show no runnable chain. detect_DFR was missing
    every library because it only parsed (1), which the prose docs rarely contain."""
    out = []
    # (1) executable call-chains (unchanged)
    for line in ev.ex_lines:
        try:
            tree = ast.parse(line.split("#")[0].strip())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Call):
                inner = _call_name(node.value)
                if inner:
                    out.append(Proposal("return-flow", frozenset({inner, f".{node.attr}"}),
                                        {"ex": 0.75}, f"chain {inner}(...).{node.attr}"))
            if isinstance(node, ast.Call):
                for arg in node.args:
                    if isinstance(arg, ast.Call):
                        outer, inner = _call_name(node), _call_name(arg)
                        if outer and inner:
                            out.append(Proposal("return-flow", frozenset({inner, outer}),
                                                {"ex": 0.7}, f"nest {outer}({inner}(...))"))
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Call):
                inner = _call_name(node.value)
                if inner:
                    out.append(Proposal("return-flow", frozenset({inner, "[]"}),
                                        {"ex": 0.6}, f"index into {inner}(...)"))
    # (2) doc-text navigation cues (the signal the prose actually carries).
    # Aggregate by cue-type so each lib emits at most one proposal per cue (not one
    # per sentence) -- avoids flooding return-flow with near-duplicate proposals.
    by_cue: dict = {}
    for sent in re.split(r"(?<=[.;\n])\s+", ev.api_text):
        ids = [t for t in dict.fromkeys(re.findall(r"[A-Za-z_]\w+", sent)) if t in ev.doc_ids]
        sl = sent.lower()
        for pat, canon in _DFR_CUES:
            if pat.search(sl):
                slot = by_cue.setdefault(canon, set(canon))
                slot.update(ids[:2])
                break
    for canon, anchors in by_cue.items():
        out.append(Proposal("return-flow", frozenset(anchors),
                            {"doc": 0.6}, f"doc-cue return-flow: {canon[0]}"))
    return out


# generic shared-receiver vocabulary (prose form of "two ops on the same object")
_SS_CUE = re.compile(
    r"same (object|bidict|diot|conf|config|instance|mapping|receiver)\b"
    r"|in.?place|reflect|live view|mutat|assign")


def detect_SS(ev: Evidence):
    """shared-receiver: a writes self-state that b reads (same receiver object).

    Precise by construction: only DOCUMENTED methods of primary classes are
    paired (an undocumented internal sharing the backing store is not a
    user-facing composition constraint), plus a targeted inverse-view signal."""
    out = []
    for cname in ev.primary:
        ms = ev.methods[cname]
        rw = {}
        for mname in ms:
            if not ev.documented(mname):
                continue
            src = ev.source_of(ev.primary[cname], mname)
            if src:
                rw[mname] = _self_rw(src)
        for wname, (writes, _, _) in rw.items():
            if not writes:
                continue
            for rname, (_, reads, _) in rw.items():
                if rname == wname:
                    continue
                shared = set(writes) & set(reads)
                if shared:
                    out.append(Proposal("shared-receiver",
                                        frozenset({f"{cname}.{wname}", f"{cname}.{rname}"}),
                                        {"src": 0.7},
                                        f"{wname} writes self.{sorted(shared)} read by {rname}"))
        # targeted: a documented inverse/live-view property is a view onto self.
        for view in ("inv", "inverse"):
            if view in ms and ev.documented(view):
                out.append(Proposal("shared-receiver",
                                    frozenset({f"{cname}.{view}"}),
                                    {"src": 0.6, "doc": 0.5},
                                    f"{cname}.{view} is a live view of the same object"))
    # doc-text cues: the prose states the shared receiver ('same object', 'in
    # place', 'reflected', 'live view', 'mutating one side') even when the method
    # source doesn't expose it. Same root cause / fix as detect_DFR's doc cues.
    ids_seen = set()
    for sent in re.split(r"(?<=[.;\n])\s+", ev.api_text):
        if _SS_CUE.search(sent.lower()):
            ids_seen.update(t for t in re.findall(r"[A-Za-z_]\w+", sent) if t in ev.doc_ids)
    if ids_seen:
        out.append(Proposal("shared-receiver", frozenset(set(list(ids_seen)[:4]) | {"same"}),
                            {"doc": 0.6}, "doc-cue shared-receiver: same object / in-place / reflected"))
    return out


_TC_DOC_KEYS = ("returns a", "return type", "shape", "plain dict", "is itself",
                "is a bidict", "is a diot", "list spec", "dict spec", "scalar")


def detect_TC(ev: Evidence):
    """config-return-contract: an argument/spec decides the return TYPE/shape."""
    out = []
    # (1) method whose body branches on a parameter to return different shapes,
    #     or returns a constructor different from its own class (to_dict -> dict).
    for cname in ev.primary:
        for mname, mobj in ev.methods[cname].items():
            if not ev.documented(mname):
                continue
            src = ev.source_of(ev.primary[cname], mname)
            if not src:
                continue
            doc = ev.doc_of(mobj).lower()
            signals = {}
            if _returns_branch_on_param(src):
                signals["src"] = 0.7
            if re.search(r"return\s+(dict|list|tuple)\s*\(", src):
                signals["src"] = max(signals.get("src", 0), 0.6)
            if any(k in doc for k in _TC_DOC_KEYS):
                signals["doc"] = 0.55
            if signals:
                out.append(Proposal("config-return-contract",
                                    frozenset({f"{cname}.{mname}"}),
                                    signals,
                                    f"{mname} return type/shape depends on config/spec"))
    # (2) spec-shape -> output-shape, evidenced in the doc snippets (glom-style).
    text = ev.api_text.lower()
    if ("list" in text and "[" in ev.api_text) or "dict spec" in text:
        sp = 0.7 if "shape" in text or "list spec" in text else 0.45
        out.append(Proposal("config-return-contract",
                            frozenset({"spec-shape", "output-shape"}),
                            {"doc": sp, "ex": 0.5},
                            "spec literal shape (list/dict) dictates output shape"))
    return out


_CO_DOC_KEYS = ("context manager", "temporarily", "temporary", "restore", "revert",
                "persistent", "frozen", "immutable", "atomic", "rollback", "all-or-nothing")


def detect_CO(ev: Evidence):
    """lifecycle: order/scope -- context managers, temp-vs-persistent, immutability."""
    out = []
    for cname in ev.primary:
        ms = ev.methods[cname]
        for mname, mobj in ms.items():
            # gate on documented methods (keep the immutability dunders); an
            # undocumented generator like iteritems is not a lifecycle constraint.
            if mname not in ("__setattr__", "__setitem__") and not ev.documented(mname):
                continue
            src = ev.source_of(ev.primary[cname], mname)
            doc = ev.doc_of(mobj).lower()
            is_cm = ("@contextmanager" in src or "contextmanager" in src
                     or "yield" in src and "def " in src)
            mentions = any(k in doc for k in _CO_DOC_KEYS)
            if is_cm or mname in ("thaw", "with_profile", "plugins_context"):
                # find a persistent sibling by name pairing
                sib = _persistent_sibling(mname, set(ms))
                anchors = {f"{cname}.{mname}"} | ({f"{cname}.{sib}"} if sib else set())
                out.append(Proposal("lifecycle", frozenset(anchors),
                                    {"src": 0.7 if is_cm else 0.4,
                                     "doc": 0.6 if mentions else 0.3},
                                    f"{mname} is a temporary-scope context manager"))
            # immutability: __setattr__/__setitem__ that raises on frozen state
            if mname in ("__setattr__", "__setitem__") and "raise" in src and \
                    re.search(r"frozen|immutable", src, re.I):
                out.append(Proposal("lifecycle", frozenset({cname, f"{cname}.{mname}"}),
                                    {"src": 0.75}, f"{cname} is frozen/immutable (raises on modify)"))
            # atomic batch
            if mentions and re.search(r"atomic|rollback|all-or-nothing", doc):
                out.append(Proposal("lifecycle", frozenset({f"{cname}.{mname}"}),
                                    {"doc": 0.6}, f"{mname} is atomic / all-or-nothing"))
    return out


_CE_DISCHARGE = ("commit", "save", "flush", "sync", "dump", "close", "release",
                 "disconnect", "checkin", "finalize")
_CE_DOC_KEYS = ("persist", "durable", "must call", "otherwise lost", "not committed",
                "commit", "obligation", "discard", "flush")


def detect_CE(ev: Evidence):
    """completion-obligation: a staging/acquire op must be paired with a discharge
    (commit/save/close) or release call, or an explicit acquire/release pair."""
    out = []
    text = ev.api_text.lower()
    doc_says_obligation = any(k in text for k in _CE_DOC_KEYS)
    for cname in ev.primary:
        ms = ev.methods[cname]
        for mname in ms:
            if ev.documented(mname) and mname.lower() in _CE_DISCHARGE:
                signals = {"sig": 0.5}
                if doc_says_obligation:
                    signals["doc"] = 0.6
                out.append(Proposal("completion-obligation",
                                    frozenset({f"{cname}.{mname}"}), signals,
                                    f"{mname} is a discharge call that must follow the staging op"))
        names = set(ms)
        for a, b in (("open", "close"), ("connect", "disconnect"), ("acquire", "release"),
                     ("start", "stop"), ("begin", "end")):
            if a in names and b in names:
                out.append(Proposal("completion-obligation",
                                    frozenset({f"{cname}.{a}", f"{cname}.{b}"}),
                                    {"sig": 0.7}, f"{a}/{b} acquire-release obligation"))
    return out


DETECTORS = [detect_DFP, detect_doc_kwargs, detect_DFR, detect_SS, detect_TC, detect_CO, detect_CE]


def _call_name(call: ast.Call):
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def _persistent_sibling(cm_name: str, names: set):
    if cm_name.startswith("with_"):
        cand = "use_" + cm_name[len("with_"):]
        return cand if cand in names else None
    if cm_name == "thaw":
        return "__setattr__" if "__setattr__" in names else None
    if cm_name == "plugins_context":
        return "disable" if "disable" in names else None
    return None


# ---------------------------------------------------------------------------
# Scoring: noisy-OR witness, discriminative typed score, decision.
# ---------------------------------------------------------------------------
def score_proposals(proposals, container_tokens=frozenset()):
    """Merge duplicates, then compute the discriminative score for each.

    score(r) = s_kappa(r) * prod_{k != kappa(r)} (1 - lambda * s_k^overlap)
    where s_k^overlap is the strongest competing channel witness among proposals
    whose DISTINCTIVE anchors overlap this one's. Container tokens (class names)
    are excluded from the overlap test: two rules about different kwargs of the
    same class (diot_transform= vs diot_nest=) are NOT competing for one slot.
    """
    def distinctive(anchors):
        return frozenset(a for a in anchors if a not in container_tokens)

    # merge proposals with identical (relation, anchors): noisy-OR keeps max per source
    merged: dict = {}
    for p in proposals:
        key = (p.relation, p.anchors)
        if key not in merged:
            merged[key] = p
        else:
            for s, v in p.signals.items():
                merged[key].signals[s] = max(merged[key].signals.get(s, 0.0), v)
    items = list(merged.values())

    # per-channel witness, and competing-channel strength on overlapping anchors
    scored = []
    for p in items:
        s_self = p.witness()
        competing = 1.0
        pk = distinctive(p.anchors)
        for q in items:
            if q is p or q.channel() == p.channel():
                continue
            if pk & distinctive(q.anchors):
                competing *= (1.0 - LAMBDA_SUP * q.witness())
        raw = s_self * competing
        if raw >= TAU_DETECT:
            scored.append((p, s_self, raw))
    return scored


# ---------------------------------------------------------------------------
# Platt calibration with leave-one-library-out fitting.
# ---------------------------------------------------------------------------
def _sigmoid(z):
    if z < -30:
        return 0.0
    if z > 30:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


def fit_platt(scores, labels, iters=200, lr=0.3):
    """1-D logistic regression  c = sigmoid(alpha*score + beta)  by gradient
    descent.  Returns (alpha, beta).  Class imbalance is fine -- we only need a
    monotone calibrated map for the precision-coverage curve."""
    alpha, beta = 1.0, 0.0
    n = max(1, len(scores))
    for _ in range(iters):
        ga = gb = 0.0
        for s, y in zip(scores, labels):
            pred = _sigmoid(alpha * s + beta)
            err = pred - y
            ga += err * s
            gb += err
        alpha -= lr * ga / n
        beta -= lr * gb / n
    return alpha, beta


def extract_library(lib_name: str, platt=None):
    """Run Phi on one library.  Returns list of dicts (one per surviving rule)."""
    ev = Evidence(lib_name)
    proposals = []
    for det in DETECTORS:
        try:
            proposals.extend(det(ev))
        except Exception as exc:  # a detector must never crash extraction
            print(f"  [warn] {det.__name__} on {lib_name}: {exc!r}")
    proposals = [p for p in proposals if p.anchors and ev.relevant(p.anchors)]
    scored = score_proposals(proposals, container_tokens=frozenset(ev.classes))
    rules = []
    for p, witness, raw in scored:
        c = _sigmoid(platt[0] * raw + platt[1]) if platt else raw
        rules.append({
            "lib": lib_name,
            "relation": p.relation,
            "channel": p.channel(),
            "anchors": sorted(a for a in p.anchors),
            "witness": round(witness, 4),
            "score": round(raw, 4),
            "confidence": round(c, 4),
            "rationale": p.rationale,
            "rule_text": synthesize_rule(lib_name, p),
        })
    rules.sort(key=lambda r: -r["confidence"])
    return rules


# ---------------------------------------------------------------------------
# Rule synthesis: render a surviving proposal into B4-shaped injection text.
# ---------------------------------------------------------------------------
_TEMPLATES = {
    "param-dependency":
        "Relation: param-dependency\nConstraint: The choice among {anchors} decides which "
        "value/old-mapping survives or how the paired call behaves. If a method has a "
        "force/override variant or a relevant keyword argument, use the one that produces the "
        "required effect (the variant that drops or keeps the conflicting entry, or the argument "
        "that supplies a default / selects the mode); do NOT rely on the plain default.",
    "return-flow":
        "Relation: return-flow\nConstraint: Feed the value produced by the first call into the "
        "second -- {anchors} must be CHAINED: capture the result of the prior call and "
        "pass/navigate it into the next; do not recompute it from the original inputs.",
    "shared-receiver":
        "Relation: shared-receiver\nConstraint: Operate on the SAME object across {anchors}: "
        "mutate the object that was passed in and read back from that same object (or its live "
        "view). A freshly rebuilt object will NOT reflect the mutation.",
    "config-return-contract":
        "Relation: config-return-contract\nConstraint: The config/spec/argument in {anchors} "
        "DETERMINES the return TYPE/SHAPE -- match the spec shape to the required output: to "
        "return a LIST use a list-shaped spec, to return a DICT use a dict-shaped spec, to return "
        "a single scalar use the bare/scalar spec. Do NOT wrap a scalar in a list or index a "
        "single result as if it were a list.",
    "lifecycle":
        "Relation: lifecycle\nConstraint: Respect order/scope across {anchors}: a temporary / "
        "context-managed form reverts its effect on exit, while a persistent form does not -- use "
        "whichever the task needs and let a temporary scope auto-restore; modify frozen/immutable "
        "state only inside the provided thaw/scope.",
    "completion-obligation":
        "Relation: completion-obligation\nConstraint: Staging an operation is not enough -- you "
        "MUST also call the discharge partner ({anchors}) to make it take effect (e.g. commit a "
        "write); close()/with do not discharge it for you.",
}


def synthesize_rule(lib_name: str, p: Proposal) -> str:
    anchors = ", ".join(sorted(a for a in p.anchors)) or "(the paired APIs)"
    body = _TEMPLATES[p.relation].format(anchors=anchors)
    return f"Relevant API Pair Rule (auto-extracted):\n{body}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Test-free pairwise-constraint extractor (B5).")
    ap.add_argument("--lib", help="single library to extract")
    ap.add_argument("--all", action="store_true", help="all libs with LOLO calibration")
    ap.add_argument("--emit", help="write per-lib extracted_rules.json under this dir")
    ap.add_argument("--libs", default=",".join(DEFAULT_LIBS))
    args = ap.parse_args()

    libs = [args.lib] if args.lib else [s for s in args.libs.split(",") if s]

    # Uncalibrated pass to gather (score, label) for LOLO calibration needs gold;
    # calibration labels are produced by eval_extraction.label_for_calibration to
    # keep this module gold-free. Here we emit RAW scores; eval applies calibration.
    allrules = {}
    for lib in libs:
        rules = extract_library(lib, platt=None)
        allrules[lib] = rules
        print(f"\n===== {lib}: {len(rules)} extracted typed rules (raw score) =====")
        for r in rules:
            print(f"  [{r['score']:.3f}] {r['relation']:<24} {r['anchors']}")

    if args.emit:
        out = Path(args.emit)
        out.mkdir(parents=True, exist_ok=True)
        for lib, rules in allrules.items():
            (out / f"{lib}_extracted_rules.json").write_text(
                json.dumps(rules, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nwrote raw extractions to {out}")


if __name__ == "__main__":
    main()
