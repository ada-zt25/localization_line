def persistent_disable_beta_then_temp_only_alpha_score(value):
    with plugins_context([sp.get_plugin('beta').name]):
        sp.hooks.enable(['alpha'])
        inside = sp.hooks.score(value)
        sp.hooks.enable(['beta', 'alpha'])
    after = sp.hooks.score(value)
    return inside, after