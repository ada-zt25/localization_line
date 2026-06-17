def disable_alpha_gamma_via_wrappers_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    sp.get_plugin('alpha').disable()
    sp.get_plugin('gamma').disable()
    return sp.hooks.score(value)