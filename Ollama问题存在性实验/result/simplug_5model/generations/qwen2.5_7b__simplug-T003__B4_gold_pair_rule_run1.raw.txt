def disable_beta_then_score(value):
    sp.disable("beta")
    return sp.hooks.score(value)