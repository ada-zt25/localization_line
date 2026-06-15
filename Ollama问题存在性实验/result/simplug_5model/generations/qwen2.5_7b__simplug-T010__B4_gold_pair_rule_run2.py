def persistent_disable_beta_then_temp_only_alpha_score(value):
    sp.disable("beta")
    with sp.plugins_context(["alpha"]):
        inside = sp.hooks.score(value)
    after = sp.hooks.score(value)
    return inside, after