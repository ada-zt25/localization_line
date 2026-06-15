def disable_alpha_gamma_then_score(value):
    with sp.plugins_context({'alpha', 'gamma'}.difference({sp.active_plugins})):
        results = sp.hooks.score(value)
    return results