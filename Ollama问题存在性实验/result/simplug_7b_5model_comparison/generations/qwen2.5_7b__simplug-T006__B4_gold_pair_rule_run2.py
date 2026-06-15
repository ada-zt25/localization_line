def disable_alpha_gamma_then_score(value):
    sp.disable("alpha")
    sp.disable("gamma")
    with sp.plugins_context(["beta"]):
        return sp.hooks.score(value)