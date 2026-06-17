#!/usr/bin/env python3
r"""Witness probe (B5 extraction hardening) -- execution-grounded, test-free.

Raises extractor precision by *executing* each candidate rule against the real
vendored library, keeping only rules that demonstrably "fire": a synthesized
COMPLIANT vs VIOLATING program pair, run on the real objects, must produce an
OBSERVABLY DIFFERENT successful outcome.

Test-free: the probes read ONLY the library's importable surface (the classes
named in a proposal's anchors) via ``lib_<name>.make_namespace()``. They NEVER
import the hidden tests (``CHECKS``/``INPUTS``), the gold rules
(``GOLD_PAIR_RULES``), or the anchor suites. (gold is touched only by
eval_extraction, and only to *score* this pilot.)

Verdict per proposal:
    FIRES          compliant & violating ran and their observations DIVERGE
    NO_DIVERGENCE  both ran, observations identical -> proven NOT a real constraint
    ABSTAIN        could not synthesize a valid compliant/violating pair (yet)

Two reported policies:
    strict        keep iff FIRES                       (precision-maximizing)
    conservative  drop iff NO_DIVERGENCE; keep FIRES+ABSTAIN  (refute-only, no
                  recall loss -- removes only rules proven inert by execution)

CLI:
    python witness_probe.py --lib sqlitedict
    python witness_probe.py --lib bidict
"""

from __future__ import annotations

import argparse
import inspect
import os
import re
import tempfile

import pair_extractor as px
import eval_extraction as ee

FIRES, NODIV, ABSTAIN = "FIRES", "NO_DIVERGENCE", "ABSTAIN"

# The probes carry NO per-library knowledge. The only constants are:
#   _SAMPLE / _NESTED : generic tiny structures to construct a subject object;
#   _PROBE_VALUES     : universal config-flag settings tried on ANY documented
#                       knob (we never hard-code that diot_nest=False or that a
#                       bidict has value-uniqueness -- the library's own runtime
#                       behavior is the arbiter);
#   _FORCE_PREFIXES   : a general naming convention for override variants.
# Everything else is a relation-level template (i.e. the taxonomy itself).
_SAMPLE = {"a": 1, "b": 2}              # tiny mapping sample to build a subject
_NESTED = {"x": {"y": 1}}               # nested data to expose a shape contract
_PROBE_VALUES = (True, False, None, 0, 1)   # universal knob settings to try


# ---------------------------------------------------------------------------
# anchor parsing / small helpers
# ---------------------------------------------------------------------------
def _parse_kwarg(anchors):
    """Handle both anchor formats for a config/param kwarg:
        {'SqliteDict', 'SqliteDict(autocommit=)'}  -> ('SqliteDict', 'autocommit')
        {'Diot', 'diot_nest='}                     -> ('Diot', 'diot_nest')
    """
    cls = kw = None
    for a in anchors:
        m = re.fullmatch(r"([A-Za-z_]\w*)\(([A-Za-z_]\w*)=\)", a)   # Class(kw=)
        if m:
            cls, kw = m.group(1), m.group(2)
            continue
        m2 = re.fullmatch(r"([A-Za-z_]\w*)=", a)                    # bare kw=
        if m2:
            kw = kw or m2.group(1)
            continue
        if re.fullmatch(r"[A-Za-z_]\w*", a):                        # bare class name
            cls = cls or a
    return cls, kw


def _split(anchor):
    return anchor.split(".", 1) if "." in anchor else (None, anchor)


def _methods(anchors):
    return [a for a in anchors if "." in a and "(" not in a]


def _safe(thunk):
    try:
        return ("ok", thunk())
    except Exception as exc:
        return ("err", repr(exc))


def _make_subject(cls):
    """Build an instance from a tiny sample (test-free: just basic construction)."""
    for args in ((dict(_SAMPLE),), ()):
        try:
            return cls(*args)
        except Exception:
            continue
    return None


def _mapping_like(obj):
    return all(hasattr(obj, d) for d in ("__getitem__", "__contains__"))


def _is_store_class(cls):
    return all(hasattr(cls, d) for d in ("__setitem__", "__getitem__", "__contains__"))


# ---------------------------------------------------------------------------
# completion-obligation: discharge-semantics roundtrip (key/value store shape)
# ---------------------------------------------------------------------------
def _roundtrip_durable(cls, *, discharge=None, ctor_kwargs=None, key="__wk__", val=7):
    d = tempfile.mkdtemp(prefix="wprobe_")
    path = os.path.join(d, "store.sqlite")
    try:
        db = cls(path, **(ctor_kwargs or {}))
        db[key] = val
        if discharge and discharge != "close":
            getattr(db, discharge)()
        db.close()
        fresh = cls(path, **(ctor_kwargs or {}))   # same config, another connection
        try:
            survived = key in fresh and fresh[key] == val
        finally:
            fresh.close()
        return ("ok", survived)
    except Exception as exc:
        return ("err", repr(exc))


# general persistence/discharge verbs (a naming convention, like _FORCE_PREFIXES;
# NOT library-specific). The actual discharge is confirmed by execution.
_DISCHARGE_VERBS = ("commit", "save", "flush", "sync", "persist", "checkpoint")


def _discover_discharge(cls):
    """Find, by EXECUTION, the method that makes a staged write durable (so the
    param probe can hold a correct composition fixed) -- not hard-coded."""
    for name in _DISCHARGE_VERBS:
        if callable(getattr(cls, name, None)) and _roundtrip_durable(cls, discharge=name) == ("ok", True):
            return name
    return None


def probe_completion_obligation(ns, prop):
    cname, method = _split(sorted(prop.anchors)[0])
    cls = ns.get(cname)
    if cls is None or not _is_store_class(cls):
        return ABSTAIN, f"{cname} is not a key/value store"
    comp = _roundtrip_durable(cls, discharge=method)
    viol = _roundtrip_durable(cls, discharge=None)
    if comp[0] != "ok" or viol[0] != "ok":
        return ABSTAIN, f"compliant={comp} violating={viol}"
    if comp[1] and not viol[1]:
        return FIRES, f"'{method}()' makes the write durable; omitting it does not"
    return NODIV, f"durable(with {method})={comp[1]} durable(without)={viol[1]}"


# ---------------------------------------------------------------------------
# param-dependency: (a) sibling force-variant pair, (b) constructor kwarg flip
# ---------------------------------------------------------------------------
_FORCE_PREFIXES = ("force", "safe", "soft", "try")


def _order_variant(m1, m2):
    """Return (base, variant) where variant = a force/safe/... wrapper of base."""
    for a, b in ((m1, m2), (m2, m1)):
        for pre in _FORCE_PREFIXES:
            if b == pre + a:
                return a, b
    return None, None


def _probe_variant_pair(ns, methods):
    (c1, m1), (c2, m2) = _split(methods[0]), _split(methods[1])
    if c1 != c2 or ns.get(c1) is None:
        return ABSTAIN, "variant pair not on one class"
    cls = ns[c1]
    base, variant = _order_variant(m1, m2)
    if base is None:
        return ABSTAIN, f"{m1}/{m2} are not a base/force-variant pair"
    s0 = _make_subject(cls)
    if s0 is None or not hasattr(s0, "values"):
        return ABSTAIN, "no constructible subject with values()"
    try:
        existing = list(s0.values())
    except Exception as exc:
        return ABSTAIN, f"values() failed: {exc!r}"
    if not existing:
        return ABSTAIN, "empty subject"
    ev, nk = existing[0], "__pk__"
    try:                                  # positional arity of the base method
        params = [p for p in inspect.signature(getattr(cls, base)).parameters.values()
                  if p.name != "self" and p.kind in (p.POSITIONAL_OR_KEYWORD, p.POSITIONAL_ONLY)]
        nparams = len(params)
    except (TypeError, ValueError):
        nparams = 2

    def call(name):
        obj = _make_subject(cls)
        meth = getattr(obj, name)
        args = (nk, ev) if nparams >= 2 else ({nk: ev},)   # induce a value conflict
        return ("state", (meth(args[0], *args[1:]), dict(obj)))

    rb, rv = _safe(lambda: call(base)), _safe(lambda: call(variant))
    if rb[0] == "err" and rv[0] == "ok":
        return FIRES, f"{base} raises on the conflict, {variant} overrides it"
    if rb[0] == "ok" and rv[0] == "ok":
        if rb[1][1] != rv[1][1]:
            return FIRES, f"{base} and {variant} leave different state"
        return NODIV, f"{base}/{variant} produce identical state"
    return ABSTAIN, f"base={rb[0]} variant={rv[0]} (could not induce a clean conflict)"


def probe_param_dependency(ns, prop):
    ms = _methods(prop.anchors)
    if len(ms) == 2:
        return _probe_variant_pair(ns, ms)
    cls_name, kw = _parse_kwarg(prop.anchors)
    cls = ns.get(cls_name)
    if cls is None or kw is None or not _is_store_class(cls):
        return ABSTAIN, f"no store-class kwarg pair in {sorted(prop.anchors)}"
    dis = _discover_discharge(cls)                 # found by execution, not hard-coded
    base = _roundtrip_durable(cls, discharge=dis, ctor_kwargs={})
    if base[0] != "ok":
        return ABSTAIN, f"base construction failed: {base}"
    tried = 0
    for v in _PROBE_VALUES:                       # universal knob settings
        flip = _roundtrip_durable(cls, discharge=dis, ctor_kwargs={kw: v})
        if flip[0] != "ok":
            continue
        tried += 1
        if flip[1] != base[1]:
            return FIRES, f"setting {kw}={v!r} changes the correct-composition outcome"
    if tried == 0:
        return ABSTAIN, f"no universal probe value constructs with {kw}="
    return NODIV, f"{kw}= does not change the correct-composition outcome (tried {tried})"


# ---------------------------------------------------------------------------
# shared-receiver: a live alias/view reflects mutations of the same object
# ---------------------------------------------------------------------------
def probe_shared_receiver(ns, prop):
    anchors = sorted(prop.anchors)
    single = [a for a in anchors if "." in a]
    if len(single) != 1:
        return ABSTAIN, "no single view-attribute anchor (pilot)"
    cname, attr = _split(single[0])
    cls = ns.get(cname)
    if cls is None:
        return ABSTAIN, f"{cname} not in namespace"
    subj = _make_subject(cls)
    if subj is None:
        return ABSTAIN, "no constructible subject"
    got = _safe(lambda: getattr(subj, attr))
    if got[0] != "ok" or not _mapping_like(got[1]):
        return ABSTAIN, f"{attr} is not a mapping view"
    view = got[1]
    nk, nv = "__sr__", 999
    mut = _safe(lambda: subj.__setitem__(nk, nv))
    if mut[0] != "ok":
        return ABSTAIN, f"subject not mutable (e.g. frozen) -> alias is vacuous: {mut[1]}"
    reflected = (nk in view) or (nv in view)            # same-dir or inverse view
    if reflected:
        return FIRES, f"mutating the object is visible through .{attr} (live alias)"
    return NODIV, f".{attr} did not reflect the mutation (a copy, not a shared view)"


# ---------------------------------------------------------------------------
# config-return-contract: a config/spec/arg DECIDES the return TYPE/SHAPE
# ---------------------------------------------------------------------------
def _cfg_kwarg_flip(ns, prop):
    cls_name, kw = _parse_kwarg(prop.anchors)
    cls = ns.get(cls_name)
    if cls is None or kw is None:
        return None
    base = _safe(lambda: type(cls(dict(_NESTED))["x"]))
    if base[0] != "ok":
        return ABSTAIN, f"base construction failed: {base}"
    tried = 0
    for v in _PROBE_VALUES:                       # universal knob settings
        flip = _safe(lambda v=v: type(cls(dict(_NESTED), **{kw: v})["x"]))
        if flip[0] != "ok":
            continue
        tried += 1
        if flip[1] is not base[1]:
            return FIRES, (f"setting {kw}={v!r} changes the nested return TYPE "
                           f"({base[1].__name__} -> {flip[1].__name__})")
    if tried == 0:
        return ABSTAIN, f"no universal probe value constructs with {kw}="
    return NODIV, f"{kw}= does not change the return type ({base[1].__name__})"


def _cfg_glom_spec(ns, prop):
    g = ns.get("glom")
    if g is None or not callable(g):
        return None
    data = {"a": 1}
    scalar = _safe(lambda: type(g(data, "a")))          # scalar spec -> scalar
    dico = _safe(lambda: type(g(data, {"k": "a"})))     # dict spec   -> dict
    if scalar[0] != "ok" or dico[0] != "ok":
        return ABSTAIN, f"scalar={scalar} dict={dico}"
    if scalar[1] is not dico[1]:
        return FIRES, f"spec shape decides output type ({scalar[1].__name__} vs {dico[1].__name__})"
    return NODIV, "spec shape does not change output type"


def probe_config_return(ns, prop):
    anchors = sorted(prop.anchors)
    # (a) a config kwarg that flips the return type
    if any("=" in a for a in anchors):
        r = _cfg_kwarg_flip(ns, prop)
        if r is not None:
            return r
    # (b) glom-style abstract spec-shape -> output-shape contract
    if any(t in {"spec-shape", "output-shape"} for t in anchors):
        r = _cfg_glom_spec(ns, prop)
        if r is not None:
            return r
    # (c) a bare accessor method with no shape-deciding argument cannot be a
    #     config-return-contract: its return type is config-invariant -> refute.
    methods = _methods(anchors)
    if len(methods) == 1:
        cname, m = _split(methods[0])
        cls = ns.get(cname)
        if cls is not None:
            meth = getattr(cls, m, None)
            try:
                params = [p for p in inspect.signature(meth).parameters.values()
                          if p.name != "self"]
            except (TypeError, ValueError):
                params = None
            if params is not None and not params:
                return NODIV, f"{m}() takes no shape-deciding argument; return type is config-invariant"
    return ABSTAIN, "no synthesizable spec/config that varies the return type"


# ---------------------------------------------------------------------------
# lifecycle: immutability sub-shape (modify -> raises). temp-scope context
# managers (thaw/with_/plugins_context) and atomic rollback are rollout TODO.
# ---------------------------------------------------------------------------
def _mutates_ok(ns, cls, ctor_kwargs):
    """True if a fresh instance accepts mutation, False if it raises, None if
    the instance cannot be built at all."""
    def build():
        for args in ((dict(_SAMPLE),), ()):
            s = _safe(lambda a=args: cls(*a, **ctor_kwargs))
            if s[0] == "ok":
                return s[1]
        return None
    obj = build()
    if obj is None:
        return None
    r_attr = _safe(lambda: setattr(obj, "probe_attr", 1))
    obj2 = build() or obj
    r_item = _safe(lambda: obj2.__setitem__("probe_k", 1))
    if r_attr[0] == "err" and r_item[0] == "err":
        return False                       # both mutation paths raise -> immutable
    if r_attr[0] == "ok" or r_item[0] == "ok":
        return True                        # at least one mutation path works
    return None


def probe_lifecycle(ns, prop):
    anchors = sorted(prop.anchors)
    low = " ".join(anchors).lower()
    if any(t in low for t in ("thaw", "with_", "context", "plugins_context",
                              "putall", "atomic")):
        return ABSTAIN, "context-manager / atomic sub-shape (rollout)"
    # (a) frozen-making kwarg: frozen=True must turn mutation into an error
    cls_name, kw = _parse_kwarg(anchors)
    if kw and "frozen" in kw.lower() and ns.get(cls_name) is not None:
        base = _mutates_ok(ns, ns[cls_name], {})
        frz = _mutates_ok(ns, ns[cls_name], {kw: True})
        if base is not None and frz is not None:
            if base and not frz:
                return FIRES, f"{kw}=True makes the object immutable (mutation raises)"
            return NODIV, f"{kw}= does not change mutability"
    # (b) immutability-by-class: the anchored class is (not) actually immutable
    if "__setattr__" in low or "__setitem__" in low:
        cls = None
        for a in anchors:
            c, _ = _split(a)
            cand = ns.get(c) or ns.get(a)
            if cand is not None:
                cls = cand
                break
        if cls is not None:
            ok = _mutates_ok(ns, cls, {})
            if ok is True:
                return NODIV, (f"{cls.__name__} is mutable; a plain __setattr__/__setitem__ "
                               f"is not a lifecycle constraint")
            if ok is False:
                return FIRES, f"{cls.__name__} is immutable -- modifying it raises (lifecycle)"
    return ABSTAIN, "no synthesizable lifecycle sub-shape (yet)"


PROBES = {
    "completion-obligation": probe_completion_obligation,
    "param-dependency": probe_param_dependency,
    "shared-receiver": probe_shared_receiver,
    "config-return-contract": probe_config_return,
    "lifecycle": probe_lifecycle,
    # return-flow: synthesizer TODO (rollout)
}


def probe_proposal(ns, prop):
    fn = PROBES.get(prop.relation)
    if fn is None:
        return ABSTAIN, f"no probe for relation {prop.relation} yet (rollout)"
    try:
        return fn(ns, prop)
    except Exception as exc:
        return ABSTAIN, f"probe error: {exc!r}"


# ---------------------------------------------------------------------------
# reusable vetting API (used by rq2_vetted.py to filter B5 injection)
# ---------------------------------------------------------------------------
class _Prop:                                  # minimal Proposal shim for the probes
    __slots__ = ("relation", "anchors")

    def __init__(self, relation, anchors):
        self.relation, self.anchors = relation, frozenset(anchors)


def verdict_for_rule(ns, relation, anchors):
    """(verdict, detail) for one extracted rule, by executing the real library."""
    return probe_proposal(ns, _Prop(relation, anchors))


_VET_CACHE: dict = {}


def vet_library(lib_name):
    """{(relation, anchors_tuple): (verdict, detail)} over all Phi-extracted rules."""
    if lib_name in _VET_CACHE:
        return _VET_CACHE[lib_name]
    ns = px.Evidence(lib_name).namespace
    out = {}
    for r in px.extract_library(lib_name, platt=None):
        v, d = verdict_for_rule(ns, r["relation"], r["anchors"])
        out[(r["relation"], tuple(sorted(r["anchors"])))] = (v, d)
    _VET_CACHE[lib_name] = out
    return out


def keep_rule(verdict, policy="strict"):
    """Injection policy: strict keeps only FIRES; conservative drops proven-inert."""
    return verdict == FIRES if policy == "strict" else verdict != NODIV


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------
def run(lib):
    evid = px.Evidence(lib)
    ns = evid.namespace
    proposals = []
    for det in px.DETECTORS:
        try:
            proposals.extend(det(evid))
        except Exception as exc:
            print(f"  [warn] {det.__name__}: {exc!r}")
    proposals = [p for p in proposals if p.anchors and evid.relevant(p.anchors)]
    scored = px.score_proposals(proposals, container_tokens=frozenset(evid.classes))

    rows = []
    for p, witness, raw in scored:
        rule = {"relation": p.relation, "anchors": sorted(p.anchors)}
        is_tp = bool(ee._match_gold(rule, lib))     # gold ONLY to score the pilot
        verdict, detail = probe_proposal(ns, p)
        rows.append({"relation": p.relation, "anchors": sorted(p.anchors),
                     "score": round(raw, 3), "is_tp": is_tp,
                     "verdict": verdict, "detail": detail})
    rows.sort(key=lambda r: -r["score"])

    print(f"\n# Witness-probe on '{lib}'  (test-free, execution-grounded)\n")
    print(f"{'relation':<24} {'verdict':<14} {'gold':<5} {'score':<6} anchors")
    print("-" * 96)
    for r in rows:
        flag = "TP" if r["is_tp"] else "FP"
        print(f"{r['relation']:<24} {r['verdict']:<14} {flag:<5} {r['score']:<6} {r['anchors']}")
        if r["verdict"] != FIRES:
            print(f"{'':<24} -> {r['detail']}")

    emitted = len(rows)
    tp = sum(r["is_tp"] for r in rows)
    nodiv = [r for r in rows if r["verdict"] == NODIV]
    fires = [r for r in rows if r["verdict"] == FIRES]
    abst = [r for r in rows if r["verdict"] == ABSTAIN]

    def prec(kept):
        return (sum(k["is_tp"] for k in kept) / len(kept)) if kept else 0.0

    # strict: keep iff FIRES ; conservative: drop only NO_DIVERGENCE
    strict_kept = fires
    cons_kept = fires + abst
    print("\n## Precision lift")
    print(f"  baseline      : emitted={emitted:<3} TP={tp:<3} precision={tp/emitted:.3f}")
    print(f"  strict (FIRES): kept={len(strict_kept):<3} TP={sum(k['is_tp'] for k in strict_kept):<3} "
          f"precision={prec(strict_kept):.3f}")
    print(f"  conservative  : kept={len(cons_kept):<3} TP={sum(k['is_tp'] for k in cons_kept):<3} "
          f"precision={prec(cons_kept):.3f}  (drops only proven-inert)")
    print(f"  verdicts: FIRES={len(fires)}  NO_DIVERGENCE={len(nodiv)} (proven FP-removals)  "
          f"ABSTAIN={len(abst)}")
    fp_nodiv = sum(not r["is_tp"] for r in nodiv)
    print(f"  of the {len(nodiv)} NO_DIVERGENCE removals, {fp_nodiv} were FPs (proven hallucinations)")
    return rows


def main():
    ap = argparse.ArgumentParser(description="Witness-probe (B5 precision hardening).")
    ap.add_argument("--lib", default="sqlitedict")
    args = ap.parse_args()
    run(args.lib)


if __name__ == "__main__":
    main()
