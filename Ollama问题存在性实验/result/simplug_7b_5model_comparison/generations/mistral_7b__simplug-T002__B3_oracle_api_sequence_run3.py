def only_alpha_gamma_score(value):
    context = sp.plugins_context()
    context.enable_plugin('alpha')
    context.enable_plugin('gamma')
    context.disable_plugin('beta')
    score = sp.hooks.score(value, context=context)
    return score