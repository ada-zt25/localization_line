def disable_alpha_gamma_via_wrappers_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context((alpha, gamma)):
        alpha.disable()
        gamma.disable()
        return sp.hooks.score(value)