def only_alpha_gamma_score(value):
    with sp.plugins_context(alpha=True, gamma=True) as plugins:
        return sp.hooks.score(value)