def disable_alpha_gamma_then_score(value):
    global sp, alpha, beta, gamma
    sp.disable(alpha)
    sp.disable(gamma)
    return sp.hooks.score(value)