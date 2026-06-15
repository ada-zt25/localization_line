def only_beta_score(value):
    context = sp.plugins_context()
    context.enable_plugin('beta')
    score = sp.hooks.score(value, context=context)
    context.disable_plugin('beta')
    return score