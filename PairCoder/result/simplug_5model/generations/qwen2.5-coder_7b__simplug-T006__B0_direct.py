def disable_alpha_gamma_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    sp.plugins.disable(alpha)
    sp.plugins.disable(gamma)
    return sp.hooks.score(value)