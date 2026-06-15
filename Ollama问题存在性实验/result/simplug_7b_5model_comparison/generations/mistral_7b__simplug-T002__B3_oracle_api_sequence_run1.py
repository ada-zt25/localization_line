def only_alpha_gamma_score(value):
    plugins_context = sp.plugins_context()
    plugins_context.enable('alpha')
    plugins_context.enable('gamma')
    plugins_context.disable('beta')
    return sp.hooks.score(value, plugins_context)