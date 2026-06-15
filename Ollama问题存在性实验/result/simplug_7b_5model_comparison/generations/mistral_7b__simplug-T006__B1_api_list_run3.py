def disable_alpha_gamma_then_score(value):
    with sp.plugins_context({'alpha', 'gamma'}: False):
        result = sp.hooks.score(value)
        sp.enable('alpha')
        sp.enable('gamma')
        return result