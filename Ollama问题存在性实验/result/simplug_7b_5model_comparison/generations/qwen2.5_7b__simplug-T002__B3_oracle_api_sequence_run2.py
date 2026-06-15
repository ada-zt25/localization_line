def only_alpha_gamma_score(value):
    with sp.plugins_context(alpha=True, beta=False, gamma=True, alpha=True):
        return sp.hooks.score(value)