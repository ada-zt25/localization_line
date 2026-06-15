def disable_alpha_gamma_then_score(value):
    with sp.plugins_context({'alpha': False, 'gamma': False}):
        return sp.hooks.score(value)