def disable_alpha_gamma_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    alpha.disable()
    gamma.disable()
    return sp.hooks.score(value)