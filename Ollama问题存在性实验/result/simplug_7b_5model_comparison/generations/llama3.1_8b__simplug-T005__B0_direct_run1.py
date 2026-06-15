def beta_only_inside_context_then_all_score(value):
    with sp.hooks.context(beta.enabled=True):
        result_beta = sp.hooks.score(value)
    result_all = sp.hooks.score(value)
    return result_beta, result_all