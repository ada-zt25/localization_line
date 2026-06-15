def only_beta_score(value):
    plugins_context = sp.plugins_context()
    plugins_context.enable('beta')
    score = sp.hooks.score(value, plugins_context=plugins_context)
    plugins_context.disable('beta')
    return score