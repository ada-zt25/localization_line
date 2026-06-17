def disable_alpha_gamma_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    sp.plugins[alpha].enabled = False
    sp.plugins[gamma].enabled = False
    result = sp.hooks.score(value)
    return result