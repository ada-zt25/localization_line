def only_beta_score(value):
    with sp.plugins_context(["beta"]):
        result = sp.hooks.score(value)
        sp.disable("beta")
        return result