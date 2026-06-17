def disable_alpha_gamma_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context(disabled=['alpha', 'gamma']):
        result = sp.hooks.score(value)
    return result