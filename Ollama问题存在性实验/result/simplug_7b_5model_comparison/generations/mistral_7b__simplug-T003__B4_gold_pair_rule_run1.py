def disable_beta_then_score(value):
    with sp.plugins_context(["beta"]):
        sp.disable("beta")
        return sp.hooks.score(value)