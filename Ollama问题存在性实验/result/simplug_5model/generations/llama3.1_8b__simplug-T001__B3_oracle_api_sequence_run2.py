def only_beta_score(value):
    with sp.plugins_context(beta=True) as plugins_context:
        return sp.hooks.score(plugins_context, value)