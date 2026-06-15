def only_beta_score(value):
    sp.hooks.score.enabled_plugins = ['beta']
    result = sp.hooks.score(value)
    return result