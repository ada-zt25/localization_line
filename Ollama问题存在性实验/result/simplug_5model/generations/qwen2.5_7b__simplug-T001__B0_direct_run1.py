def only_beta_score(value):
    with sp.hooks.enabled('beta'):
        return sp.hooks.score(value)