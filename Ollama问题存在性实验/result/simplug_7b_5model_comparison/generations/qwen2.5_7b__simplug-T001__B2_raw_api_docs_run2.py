def only_beta_score(value):
    with sp.plugins_context([beta]):
        disable(alpha, gamma)
        return sp.hooks.score(value)