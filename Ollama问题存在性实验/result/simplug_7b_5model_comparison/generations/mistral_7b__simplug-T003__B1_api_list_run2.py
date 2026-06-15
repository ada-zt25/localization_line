def disable_beta_then_score(value):
    with sp.plugins_context({'beta': False}):
        result = sp.hooks.score(value)
    return result