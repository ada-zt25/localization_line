def only_alpha_gamma_score(value):
    with sp.hooks.enabled(alpha=True, beta=False, gamma=True):
        return sp.hooks.score(value)