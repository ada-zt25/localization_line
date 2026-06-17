def disable_alpha_gamma_via_wrappers_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with plugins_context([alpha]):
        alpha.wrapper.disable()
    with plugins_context([gamma]):
        gamma.wrapper.disable()
    return sp.hooks.score(value)