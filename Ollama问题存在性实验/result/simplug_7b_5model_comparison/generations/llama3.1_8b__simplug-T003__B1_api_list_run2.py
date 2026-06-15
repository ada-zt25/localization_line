def disable_beta_then_score(value):
    with sp.plugins_context(disabled=['beta']):
        return sp.hooks.score(value)