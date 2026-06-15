def only_beta_score(value):
    sp.hooks.score.plugins = [plugin for plugin in sp.hooks.score.plugins if plugin.name != 'alpha']
    result = sp.hooks.score(value)
    return result