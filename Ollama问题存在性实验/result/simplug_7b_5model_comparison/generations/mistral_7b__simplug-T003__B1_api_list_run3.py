def disable_beta_then_score(value):
    with sp.plugins_context([plugin for plugin in sp.plugins if plugin.name != 'beta']):
        return sp.hooks.score(value)