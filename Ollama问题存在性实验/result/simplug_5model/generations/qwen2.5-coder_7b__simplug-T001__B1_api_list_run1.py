def only_beta_score(value):
    with sp.plugins_context(plugins=[beta]):
        return sp.hooks.score(value)