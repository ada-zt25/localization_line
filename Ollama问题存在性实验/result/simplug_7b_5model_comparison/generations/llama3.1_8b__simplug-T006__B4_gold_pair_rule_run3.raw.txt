def disable_alpha_gamma_then_score(value):
    global alpha, gamma
    sp.disable(alpha.name)
    sp.disable(gamma.name)
    return sp.hooks.score(value)