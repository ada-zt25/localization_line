def only_alpha_gamma_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context(["alpha", "gamma"]):
        result = sp.hooks.score(value)
    return result