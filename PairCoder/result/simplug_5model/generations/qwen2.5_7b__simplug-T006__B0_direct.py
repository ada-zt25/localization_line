def disable_alpha_gamma_then_score(value):
    _, alpha, beta, gamma = make_score_manager()
    alpha.disable_by_name()
    gamma.disable_by_name()
    return sp.hooks.score(value)