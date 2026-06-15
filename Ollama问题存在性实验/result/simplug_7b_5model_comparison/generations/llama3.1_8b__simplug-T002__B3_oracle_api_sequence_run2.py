def only_alpha_gamma_score(value):
    with sp.plugins_context(alpha=True, gamma=True) as ctx:
        return sp.hooks.score(ctx, value)