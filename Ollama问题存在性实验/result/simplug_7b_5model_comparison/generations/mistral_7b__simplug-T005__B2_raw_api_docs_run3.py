def beta_only_inside_context_then_all_score(value):
    with simplug.plugins_context([sp.get_plugin('beta')]):
        sp.disable(['alpha', 'gamma'])
        sp.enable(['beta'])
        result1 = sp.hooks.score(value)
        sp.enable(['alpha', 'gamma'])
        sp.disable(['beta'])
        result2 = sp.hooks.score(value)
    return result1, result2