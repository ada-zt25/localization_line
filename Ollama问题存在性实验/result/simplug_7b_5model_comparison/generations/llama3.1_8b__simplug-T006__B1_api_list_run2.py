def disable_alpha_gamma_then_score(value):
    with sp.plugins_context(disabled=['alpha', 'gamma']):
        return sp.hooks.score(value)