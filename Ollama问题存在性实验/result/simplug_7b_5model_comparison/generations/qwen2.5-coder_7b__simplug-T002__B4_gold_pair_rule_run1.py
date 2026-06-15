def only_alpha_gamma_score(value):
    with sp.plugins_context(["alpha", "gamma"]):
        result = sp.hooks.score(value)
    return result