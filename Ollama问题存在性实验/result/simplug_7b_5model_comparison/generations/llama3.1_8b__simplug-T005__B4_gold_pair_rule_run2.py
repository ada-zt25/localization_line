def beta_only_inside_context_then_all_score(value):
    with sp.plugins_context(["beta"]):
        result_with_beta = sp.hooks.score(value)
    original_state = sp.get_plugin("alpha").disable()
    sp.get_plugin("gamma").disable()
    sp.get_plugin("beta").disable()
    result_without_beta = sp.hooks.score(value)
    return result_with_beta, result_without_beta