def beta_only_inside_context_then_all_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context(disabled=['alpha', 'gamma']):
        result1 = sp.hooks.score(value)
    result2 = sp.hooks.score(value)
    return result1, result2