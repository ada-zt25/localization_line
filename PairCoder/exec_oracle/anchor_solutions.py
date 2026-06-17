#!/usr/bin/env python3
"""Anchoring suite for the execution oracle (P1 completion evidence).

Two claims are anchored, per task:

1. SOUNDNESS -- "violating the pair constraint makes the hidden test fail":
   for every documented violation pattern (the ones the gold pair rules
   warn about, plus typical substitutes), the hidden test MUST fail, with
   the expected reason class.

2. SEMANTIC TOLERANCE -- "semantically correct but syntactically different
   solutions pass": canonical solutions AND legitimate variants that the
   STATIC checker rejects (e.g. '-alpha'/'-gamma' subtractive context,
   manual disable/enable with restoration) MUST pass. These witness the
   static oracle's false positives.

Consumed by lib_simplug (the benchlib interface); run the gate with
``python3 benchlib.py simplug``. The full evaluation refuses to run unless green.

Each entry: (name, code, expectation) where expectation is True (must pass)
or a set of acceptable failure reasons (must fail with one of them).
"""

ANCHORS = {
    "simplug-T001": [
        (
            "canonical_context_names",
            '''
def only_beta_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context(["beta"]):
        result = sp.hooks.score(value)
    return result
''',
            True,
        ),
        (
            "variant_global_sp",
            '''
def only_beta_score(value):
    with sp.plugins_context(["beta"]):
        return sp.hooks.score(value)
''',
            True,
        ),
        (
            "variant_minus_prefix_static_fp",
            '''
def only_beta_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context(["-alpha", "-gamma"]):
        result = sp.hooks.score(value)
    return result
''',
            True,
        ),
        (
            "variant_manual_disable_enable_static_fp",
            '''
def only_beta_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    sp.disable("alpha", "gamma")
    try:
        result = sp.hooks.score(value)
    finally:
        sp.enable("alpha", "gamma")
    return result
''',
            True,
        ),
        (
            "violation_object_instead_of_name",
            '''
def only_beta_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context([beta]):
        result = sp.hooks.score(value)
    return result
''',
            {"wrong_output"},
        ),
        (
            "violation_no_selection",
            '''
def only_beta_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    return sp.hooks.score(value)
''',
            {"wrong_output"},
        ),
        (
            "violation_not_restored",
            '''
def only_beta_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    sp.disable("alpha", "gamma")
    return sp.hooks.score(value)
''',
            {"state_not_restored"},
        ),
        (
            "violation_hallucinated_api",
            '''
def only_beta_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.hooks.enabled("beta"):
        return sp.hooks.score(value)
''',
            {"runtime_error"},
        ),
    ],
    "simplug-T002": [
        (
            "canonical_context_names",
            '''
def only_alpha_gamma_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context(["alpha", "gamma"]):
        result = sp.hooks.score(value)
    return result
''',
            True,
        ),
        (
            "variant_minus_beta_static_fp",
            '''
def only_alpha_gamma_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context(["-beta"]):
        result = sp.hooks.score(value)
    return result
''',
            True,
        ),
        (
            "violation_objects_instead_of_names",
            '''
def only_alpha_gamma_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context([alpha, gamma]):
        result = sp.hooks.score(value)
    return result
''',
            {"wrong_output"},
        ),
    ],
    "simplug-T003": [
        (
            "canonical_disable_by_name",
            '''
def disable_beta_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    sp.disable("beta")
    return sp.hooks.score(value)
''',
            True,
        ),
        (
            "variant_wrapper_route",
            '''
def disable_beta_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    sp.get_plugin("beta").disable()
    return sp.hooks.score(value)
''',
            True,
        ),
        (
            "violation_context_substitute_not_persistent",
            '''
def disable_beta_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context(["alpha", "gamma"]):
        result = sp.hooks.score(value)
    return result
''',
            {"disable_not_persistent"},
        ),
        (
            "violation_object_instead_of_name",
            '''
def disable_beta_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    sp.disable(beta)
    return sp.hooks.score(value)
''',
            {"runtime_error"},
        ),
    ],
    "simplug-T004": [
        (
            "canonical_wrapper_route",
            '''
def get_beta_wrapper_disable_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    wrapper = sp.get_plugin("beta")
    wrapper.disable()
    result = sp.hooks.score(value)
    return result
''',
            True,
        ),
        (
            "variant_chained_call",
            '''
def get_beta_wrapper_disable_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    sp.get_plugin("beta").disable()
    return sp.hooks.score(value)
''',
            True,
        ),
        (
            "violation_sp_disable_shortcut",
            '''
def get_beta_wrapper_disable_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    sp.disable("beta")
    return sp.hooks.score(value)
''',
            {"mechanism_not_used"},
        ),
        (
            "violation_get_plugin_object_arg",
            '''
def get_beta_wrapper_disable_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    wrapper = sp.get_plugin(beta)
    wrapper.disable()
    return sp.hooks.score(value)
''',
            {"runtime_error"},
        ),
        (
            "violation_wrapper_fetched_not_used",
            '''
def get_beta_wrapper_disable_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    wrapper = sp.get_plugin("beta")
    beta.disable()
    return sp.hooks.score(value)
''',
            {"runtime_error"},
        ),
    ],
    "simplug-T005": [
        (
            "canonical_two_phase",
            '''
def beta_only_inside_context_then_all_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context(["beta"]):
        inside = sp.hooks.score(value)
    after = sp.hooks.score(value)
    return inside, after
''',
            True,
        ),
        (
            "variant_list_return",
            '''
def beta_only_inside_context_then_all_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    results = []
    with sp.plugins_context(["beta"]):
        results.append(sp.hooks.score(value))
    results.append(sp.hooks.score(value))
    return results
''',
            True,
        ),
        (
            "violation_single_call",
            '''
def beta_only_inside_context_then_all_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context(["beta"]):
        inside = sp.hooks.score(value)
    return inside
''',
            {"wrong_output_structure"},
        ),
        (
            "violation_second_call_inside_context",
            '''
def beta_only_inside_context_then_all_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context(["beta"]):
        inside = sp.hooks.score(value)
        after = sp.hooks.score(value)
    return inside, after
''',
            {"wrong_output"},
        ),
    ],
    "simplug-T006": [
        (
            "canonical_disable_two_names",
            '''
def disable_alpha_gamma_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    sp.disable("alpha", "gamma")
    return sp.hooks.score(value)
''',
            True,
        ),
        (
            "variant_two_calls",
            '''
def disable_alpha_gamma_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    sp.disable("alpha")
    sp.disable("gamma")
    return sp.hooks.score(value)
''',
            True,
        ),
        (
            "violation_only_alpha_disabled",
            '''
def disable_alpha_gamma_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    sp.disable("alpha")
    return sp.hooks.score(value)
''',
            {"wrong_output"},
        ),
        (
            "violation_context_substitute_not_persistent",
            '''
def disable_alpha_gamma_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context(["beta"]):
        result = sp.hooks.score(value)
    return result
''',
            {"disable_not_persistent"},
        ),
    ],
    # === 5th pair type: config -> return-contract (result mode) ===
    "simplug-T007": [
        (
            "canonical_return_single",
            '''
def first_score(value):
    sp, alpha, beta, gamma = make_first_score_manager()
    return sp.hooks.score(value)
''',
            True,
        ),
        (
            "variant_assign_then_return",
            '''
def first_score(value):
    sp, alpha, beta, gamma = make_first_score_manager()
    result = sp.hooks.score(value)
    return result
''',
            True,
        ),
        (
            "violation_wrap_in_list",
            '''
def first_score(value):
    sp, alpha, beta, gamma = make_first_score_manager()
    return [sp.hooks.score(value)]
''',
            {"wrong_output_structure"},
        ),
        (
            "violation_index_assuming_list",
            '''
def first_score(value):
    sp, alpha, beta, gamma = make_first_score_manager()
    return sp.hooks.score(value)[0]
''',
            {"wrong_output"},
        ),
    ],
    "simplug-T008": [
        (
            "canonical_return_single",
            '''
def last_score(value):
    sp, alpha, beta, gamma = make_last_score_manager()
    return sp.hooks.score(value)
''',
            True,
        ),
        (
            "violation_wrap_in_list",
            '''
def last_score(value):
    sp, alpha, beta, gamma = make_last_score_manager()
    return [sp.hooks.score(value)]
''',
            {"wrong_output_structure"},
        ),
        (
            "violation_first_instead_of_last",
            '''
def last_score(value):
    sp, alpha, beta, gamma = make_first_score_manager()
    return sp.hooks.score(value)
''',
            {"wrong_output"},
        ),
    ],
    # === return-flow rebalance: two wrappers ===
    "simplug-T009": [
        (
            "canonical_two_wrappers",
            '''
def disable_alpha_gamma_via_wrappers_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    sp.get_plugin("alpha").disable()
    sp.get_plugin("gamma").disable()
    return sp.hooks.score(value)
''',
            True,
        ),
        (
            "variant_assign_wrappers",
            '''
def disable_alpha_gamma_via_wrappers_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    wa = sp.get_plugin("alpha")
    wa.disable()
    wg = sp.get_plugin("gamma")
    wg.disable()
    return sp.hooks.score(value)
''',
            True,
        ),
        (
            "violation_sp_disable_shortcut",
            '''
def disable_alpha_gamma_via_wrappers_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    sp.disable("alpha", "gamma")
    return sp.hooks.score(value)
''',
            {"mechanism_not_used"},
        ),
        (
            "violation_get_plugin_object_arg",
            '''
def disable_alpha_gamma_via_wrappers_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    sp.get_plugin(alpha).disable()
    sp.get_plugin(gamma).disable()
    return sp.hooks.score(value)
''',
            {"runtime_error"},
        ),
    ],
    # === lifecycle rebalance: persistent disable survives temporary context ===
    "simplug-T010": [
        (
            "canonical_persistent_then_context",
            '''
def persistent_disable_beta_then_temp_only_alpha_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    sp.disable("beta")
    with sp.plugins_context(["alpha"]):
        inside = sp.hooks.score(value)
    after = sp.hooks.score(value)
    return inside, after
''',
            True,
        ),
        (
            "violation_beta_not_disabled_persistently",
            '''
def persistent_disable_beta_then_temp_only_alpha_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context(["alpha"]):
        inside = sp.hooks.score(value)
    after = sp.hooks.score(value)
    return inside, after
''',
            {"wrong_output"},
        ),
        (
            "violation_second_call_inside_context",
            '''
def persistent_disable_beta_then_temp_only_alpha_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    sp.disable("beta")
    with sp.plugins_context(["alpha"]):
        inside = sp.hooks.score(value)
        after = sp.hooks.score(value)
    return inside, after
''',
            {"wrong_output"},
        ),
    ],
}
