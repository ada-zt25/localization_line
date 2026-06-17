def beta_only_inside_context_then_all_score(value):
    sp, alpha, beta, gamma = make_score_manager()

    with sp.plugins_context(["alpha"]):
        inside = sp.hooks.score(value)
        sp.disable("beta")
        beta.disable()

    after = sp.hooks.score(value)

    # Enable beta again to restore the original state
    sp.enable("beta")
    beta.enable()

    return inside, after