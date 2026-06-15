def disable_beta_then_score(value):
    sp.disable(beta.name)
    return sp.hooks.score(value)