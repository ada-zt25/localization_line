def beta_only_inside_context_then_all_score(value):
    with sp.plugins_context(beta=True, alpha=False, gamma=False):
        beta_result = sp.hooks.score(value)
    all_result = sp.hooks.score(value)
    return beta_result, all_result