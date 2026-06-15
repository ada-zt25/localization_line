def beta_only_inside_context_then_all_score(value):
    with plugins_context([sp.get_plugin('beta').name]):
        sp.disable(['alpha', 'gamma'])
        sp.enable(['beta'])
        beta_result = sp.hooks.score(value)
        sp.enable(['alpha', 'gamma'])
        sp.disable(['beta'])
        all_result = sp.hooks.score(value)
    return beta_result, all_result