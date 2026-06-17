#!/usr/bin/env python3
"""Hidden, execution-based tests for the six simplug pair-composition tasks.

Each test consumes ONLY runtime observations:
  * the function's return value,
  * the instrumented trace (score calls with enabled-plugin sets and
    forwarded values; get_plugin / wrapper.disable / sp.disable events),
  * the final enabled-state of each manager after the call returns.

It never inspects source code, so "semantically right, written differently"
solutions pass, and "passes the static pattern but breaks at runtime"
solutions fail. This is the execution oracle that replaces the circular
static checker (P1).

Pass criteria are derived from the TASK TEXT (observable contract), not from
the injected pair rules:

  T001 only_beta_score(v)
      returns the hook results collected while ONLY beta was enabled
      (== [("beta", 2v)]); a score call with enabled == {beta} and value v
      must exist; "temporarily" => the manager's state is restored (all
      three enabled) after the function returns.
  T002 only_alpha_gamma_score(v)
      same with enabled == {alpha, gamma}; restored afterwards.
  T003 disable_beta_then_score(v)
      "disable beta" is persistent: score runs with {alpha, gamma} and beta
      REMAINS disabled after the function returns.
  T004 get_beta_wrapper_disable_then_score(v)
      behavior of T003, plus the task prescribes the mechanism: a direct
      sp.get_plugin("beta") call must occur and the RETURNED wrapper's
      .disable() must be invoked (observed at runtime, return-flow pair),
      both before the qualifying score call, on the same manager.
  T005 beta_only_inside_context_then_all_score(v)
      returns both results (any 2-sequence): first collected with {beta}
      enabled, then -- after the context exits -- with all three enabled,
      in that order, on the same manager; state restored at the end.
  T006 disable_alpha_gamma_then_score(v)
      score runs with only {beta}; alpha and gamma REMAIN disabled after
      the function returns.

Reason codes (fine-grained):
  function_not_defined | syntax_error | import_time_error | runtime_error |
  timeout | wrong_output | wrong_output_structure | no_score_call |
  wrong_enabled_set | state_not_restored | disable_not_persistent |
  mechanism_not_used | harness_error

Coarse classes (for aggregation):
  exec_error      <- syntax_error, import_time_error, runtime_error,
                     timeout, function_not_defined
  wrong_behavior  <- wrong_output, wrong_output_structure, no_score_call,
                     wrong_enabled_set
  pair_state_violation <- state_not_restored, disable_not_persistent,
                     mechanism_not_used
"""

from __future__ import annotations

from fixture_simplug import PLUGIN_NAMES, expected_result, expected_results

FUNC_NAMES = {
    "simplug-T001": "only_beta_score",
    "simplug-T002": "only_alpha_gamma_score",
    "simplug-T003": "disable_beta_then_score",
    "simplug-T004": "get_beta_wrapper_disable_then_score",
    "simplug-T005": "beta_only_inside_context_then_all_score",
    "simplug-T006": "disable_alpha_gamma_then_score",
    # --- expansion: 5th pair type (config->return-contract) + rebalance ---
    "simplug-T007": "first_score",
    "simplug-T008": "last_score",
    "simplug-T009": "disable_alpha_gamma_via_wrappers_then_score",
    "simplug-T010": "persistent_disable_beta_then_temp_only_alpha_score",
}

ALL = set(PLUGIN_NAMES)

COARSE = {
    "syntax_error": "exec_error",
    "import_time_error": "exec_error",
    "runtime_error": "exec_error",
    "timeout": "exec_error",
    "function_not_defined": "exec_error",
    "wrong_output": "wrong_behavior",
    "wrong_output_structure": "wrong_behavior",
    "no_score_call": "wrong_behavior",
    "wrong_enabled_set": "wrong_behavior",
    "state_not_restored": "pair_state_violation",
    "disable_not_persistent": "pair_state_violation",
    "mechanism_not_used": "pair_state_violation",
    "harness_error": "exec_error",
    "": "",
}


def norm(x):
    """Normalize tuples/lists recursively for order-preserving comparison."""
    if isinstance(x, (list, tuple)):
        return [norm(i) for i in x]
    return x


def _call_value(ev, v):
    """Did this score event forward the test value v?"""
    if ev.get("args"):
        return ev["args"][0] == v
    return ev.get("kwargs", {}).get("value") == v


def _score_events(events):
    return [e for e in events if e["event"] == "score" and "error" not in e]


def _fail(reason, detail):
    return {"ok": False, "reason": reason, "detail": detail}


def _ok():
    return {"ok": True, "reason": "", "detail": ""}


def _qualifying(events, v, enabled_set, expected):
    """Score events with the right enabled set, value and result."""
    out = []
    for idx, e in enumerate(events):
        if e["event"] != "score" or "error" in e:
            continue
        if set(e["enabled"]) == enabled_set and _call_value(e, v) and norm(
            e.get("result")
        ) == norm(expected):
            out.append((idx, e))
    return out


def _single_phase_check(
    ret,
    events,
    final_state,
    v,
    enabled_set,
    expect_final,
    persistent_reason,
):
    """Shared logic for T001/T002/T003/T006 (one qualifying score call)."""
    expected = expected_results(enabled_set, v)
    if norm(ret) != norm(expected):
        return _fail(
            "wrong_output",
            f"returned {ret!r}, expected {expected!r}",
        ), None
    scores = _score_events(events)
    if not scores:
        return _fail("no_score_call", "hooks.score was never called"), None
    quals = _qualifying(events, v, enabled_set, expected)
    if not quals:
        seen = [sorted(e["enabled"]) for e in scores]
        return _fail(
            "wrong_enabled_set",
            f"no score call ran with enabled == {sorted(enabled_set)}; "
            f"observed enabled sets: {seen}",
        ), None
    # any qualifying event whose manager ends in the expected final state
    for idx, e in quals:
        m = e["manager"]
        if set(final_state.get(m, [])) == expect_final:
            return _ok(), (idx, e)
    m = quals[-1][1]["manager"]
    return _fail(
        persistent_reason,
        f"manager {m} final enabled == {sorted(final_state.get(m, []))}, "
        f"expected {sorted(expect_final)}",
    ), None


def check_t001(ret, events, final_state, v):
    verdict, _ = _single_phase_check(
        ret, events, final_state, v,
        enabled_set={"beta"},
        expect_final=ALL,
        persistent_reason="state_not_restored",
    )
    return verdict


def check_t002(ret, events, final_state, v):
    verdict, _ = _single_phase_check(
        ret, events, final_state, v,
        enabled_set={"alpha", "gamma"},
        expect_final=ALL,
        persistent_reason="state_not_restored",
    )
    return verdict


def check_t003(ret, events, final_state, v):
    verdict, _ = _single_phase_check(
        ret, events, final_state, v,
        enabled_set={"alpha", "gamma"},
        expect_final={"alpha", "gamma"},
        persistent_reason="disable_not_persistent",
    )
    return verdict


def check_t004(ret, events, final_state, v):
    verdict, qual = _single_phase_check(
        ret, events, final_state, v,
        enabled_set={"alpha", "gamma"},
        expect_final={"alpha", "gamma"},
        persistent_reason="disable_not_persistent",
    )
    if not verdict["ok"]:
        return verdict
    qidx, qev = qual
    m = qev["manager"]
    gp_idx = [
        i
        for i, e in enumerate(events[:qidx])
        if e["event"] == "get_plugin" and e["manager"] == m and e["name"] == "beta"
    ]
    wd_idx = [
        i
        for i, e in enumerate(events[:qidx])
        if e["event"] == "wrapper_disable"
        and e["manager"] == m
        and e["plugin"] == "beta"
    ]
    if not gp_idx or not wd_idx or min(gp_idx) > max(wd_idx):
        return _fail(
            "mechanism_not_used",
            "task prescribes get_plugin('beta') -> wrapper.disable(); "
            f"observed get_plugin events at {gp_idx}, wrapper_disable at "
            f"{wd_idx} (before the qualifying score call)",
        )
    return _ok()


def check_t005(ret, events, final_state, v):
    if not isinstance(ret, (list, tuple)) or len(ret) != 2:
        return _fail(
            "wrong_output_structure",
            f"expected two results (inside-context, after-context); got {ret!r}",
        )
    r1, r2 = ret[0], ret[1]
    exp1 = expected_results({"beta"}, v)
    exp2 = expected_results(ALL, v)
    if norm(r1) != norm(exp1) or norm(r2) != norm(exp2):
        return _fail(
            "wrong_output",
            f"returned ({r1!r}, {r2!r}), expected ({exp1!r}, {exp2!r})",
        )
    q1 = _qualifying(events, v, {"beta"}, exp1)
    q2 = _qualifying(events, v, ALL, exp2)
    pairs = [
        (i1, e1, i2, e2)
        for i1, e1 in q1
        for i2, e2 in q2
        if i1 < i2 and e1["manager"] == e2["manager"]
    ]
    if not pairs:
        scores = _score_events(events)
        seen = [sorted(e["enabled"]) for e in scores]
        return _fail(
            "wrong_enabled_set",
            "need a {beta}-only score call followed by an all-enabled score "
            f"call on the same manager; observed enabled sets: {seen}",
        )
    for _, e1, _, _ in pairs:
        m = e1["manager"]
        if set(final_state.get(m, [])) == ALL:
            return _ok()
    m = pairs[-1][1]["manager"]
    return _fail(
        "state_not_restored",
        f"manager {m} final enabled == {sorted(final_state.get(m, []))}, "
        f"expected {sorted(ALL)}",
    )


def check_t006(ret, events, final_state, v):
    verdict, _ = _single_phase_check(
        ret, events, final_state, v,
        enabled_set={"beta"},
        expect_final={"beta"},
        persistent_reason="disable_not_persistent",
    )
    return verdict


# ---------------------------------------------------------------------------
# Expansion: 5th pair type (config -> return-contract) and rebalancing tasks
# ---------------------------------------------------------------------------


def _single_result_check(ret, events, final_state, v, position):
    """T007/T008: the spec's result-mode (FIRST/LAST) makes hooks.score return a
    SINGLE result, not a list. No state change -- all three stay enabled.
    """
    ordered = [n for n in PLUGIN_NAMES if n in ALL]  # registration order
    name = ordered[0] if position == "first" else ordered[-1]
    expected = expected_result(name, v)  # a single ("name", number) tuple
    if isinstance(ret, list):
        return _fail(
            "wrong_output_structure",
            f"returned a list {ret!r}; this hook is configured result="
            f"{position.upper()} and returns a SINGLE result {expected!r}",
        )
    if norm(ret) != norm(expected):
        return _fail(
            "wrong_output",
            f"returned {ret!r}, expected the single {position} result {expected!r}",
        )
    scores = _score_events(events)
    if not scores:
        return _fail("no_score_call", "hooks.score was never called")
    quals = [
        (idx, e)
        for idx, e in enumerate(events)
        if e["event"] == "score"
        and "error" not in e
        and set(e["enabled"]) == ALL
        and _call_value(e, v)
        and norm(e.get("result")) == norm(expected)
    ]
    if not quals:
        seen = [sorted(e["enabled"]) for e in scores]
        return _fail(
            "wrong_enabled_set",
            f"no single-result score call with all plugins enabled and value {v}; "
            f"observed enabled sets: {seen}",
        )
    for _, e in quals:
        if set(final_state.get(e["manager"], [])) == ALL:
            return _ok()
    m = quals[-1][1]["manager"]
    return _fail(
        "state_not_restored",
        f"manager {m} final enabled == {sorted(final_state.get(m, []))}, "
        f"expected {sorted(ALL)} (the function must not change enabled state)",
    )


def check_t007(ret, events, final_state, v):
    return _single_result_check(ret, events, final_state, v, "first")


def check_t008(ret, events, final_state, v):
    return _single_result_check(ret, events, final_state, v, "last")


def check_t009(ret, events, final_state, v):
    """return-flow x2: alpha and gamma must each be disabled via
    get_plugin(name) -> wrapper.disable() (not sp.disable), persistently.
    """
    verdict, qual = _single_phase_check(
        ret, events, final_state, v,
        enabled_set={"beta"},
        expect_final={"beta"},
        persistent_reason="disable_not_persistent",
    )
    if not verdict["ok"]:
        return verdict
    qidx, qev = qual
    m = qev["manager"]
    for pname in ("alpha", "gamma"):
        gp_idx = [
            i
            for i, e in enumerate(events[:qidx])
            if e["event"] == "get_plugin" and e["manager"] == m and e["name"] == pname
        ]
        wd_idx = [
            i
            for i, e in enumerate(events[:qidx])
            if e["event"] == "wrapper_disable"
            and e["manager"] == m
            and e["plugin"] == pname
        ]
        if not gp_idx or not wd_idx or min(gp_idx) > max(wd_idx):
            return _fail(
                "mechanism_not_used",
                f"task prescribes get_plugin('{pname}') -> wrapper.disable(); "
                f"observed get_plugin at {gp_idx}, wrapper_disable at {wd_idx} "
                "(before the qualifying score call)",
            )
    return _ok()


def check_t010(ret, events, final_state, v):
    """lifecycle: a persistent disable("beta") must survive a temporary
    plugins_context(["alpha"]); after the context exits, the state restores to
    what held AT ENTRY ({alpha, gamma}), not "all enabled".
    """
    if not isinstance(ret, (list, tuple)) or len(ret) != 2:
        return _fail(
            "wrong_output_structure",
            f"expected two results (inside-context, after-context); got {ret!r}",
        )
    r1, r2 = ret[0], ret[1]
    exp1 = expected_results({"alpha"}, v)
    exp2 = expected_results({"alpha", "gamma"}, v)
    if norm(r1) != norm(exp1) or norm(r2) != norm(exp2):
        return _fail(
            "wrong_output",
            f"returned ({r1!r}, {r2!r}), expected ({exp1!r}, {exp2!r}); "
            "after the context, beta must STILL be disabled",
        )
    q1 = _qualifying(events, v, {"alpha"}, exp1)
    q2 = _qualifying(events, v, {"alpha", "gamma"}, exp2)
    pairs = [
        (i1, e1, i2, e2)
        for i1, e1 in q1
        for i2, e2 in q2
        if i1 < i2 and e1["manager"] == e2["manager"]
    ]
    if not pairs:
        scores = _score_events(events)
        seen = [sorted(e["enabled"]) for e in scores]
        return _fail(
            "wrong_enabled_set",
            "need an {alpha}-only score call followed by an {alpha,gamma} score "
            f"call on the same manager; observed enabled sets: {seen}",
        )
    for _, e1, _, _ in pairs:
        m = e1["manager"]
        if set(final_state.get(m, [])) == {"alpha", "gamma"}:
            return _ok()
    m = pairs[-1][1]["manager"]
    return _fail(
        "disable_not_persistent",
        f"manager {m} final enabled == {sorted(final_state.get(m, []))}, "
        "expected ['alpha', 'gamma'] (beta's persistent disable must survive "
        "the temporary context)",
    )


CHECKS = {
    "simplug-T001": check_t001,
    "simplug-T002": check_t002,
    "simplug-T003": check_t003,
    "simplug-T004": check_t004,
    "simplug-T005": check_t005,
    "simplug-T006": check_t006,
    "simplug-T007": check_t007,
    "simplug-T008": check_t008,
    "simplug-T009": check_t009,
    "simplug-T010": check_t010,
}
