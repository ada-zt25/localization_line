def only_beta_score(value):
    with sp.plugins_context(beta=True) as ctx:
        return sp.hooks.score(ctx, value)