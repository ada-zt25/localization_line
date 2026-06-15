def beta_only_inside_context_then_all_score(value):
    with sp.plugins_context(beta):
        temp_result = sp.hooks.score(value)
        original_state = [alpha.enabled, beta.enabled, gamma.enabled]
        sp.enable(alpha.name, beta.name, gamma.name)
    all_results = sp.hooks.score(value)
    return temp_result, all_results