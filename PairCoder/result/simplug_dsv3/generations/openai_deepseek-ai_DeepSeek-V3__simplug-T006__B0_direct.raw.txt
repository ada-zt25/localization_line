def disable_alpha_gamma_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    sp.disable(alpha.name)
    sp.disable(gamma.name)
    return sp.hooks.score(value)