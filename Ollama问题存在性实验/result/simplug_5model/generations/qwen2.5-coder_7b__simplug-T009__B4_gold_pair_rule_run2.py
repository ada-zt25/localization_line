def disable_alpha_gamma_via_wrappers_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    wrapper_alpha = sp.get_plugin("alpha")
    wrapper_alpha.disable()
    wrapper_gamma = sp.get_plugin("gamma")
    wrapper_gamma.disable()
    result = sp.hooks.score(value)
    return result