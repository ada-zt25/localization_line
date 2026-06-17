def disable_alpha_gamma_via_wrappers_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context([alpha]):
        pass
    alpha_wrapper = sp.get_plugin('alpha')
    alpha_wrapper.disable()
    with sp.plugins_context([gamma]):
        pass
    gamma_wrapper = sp.get_plugin('gamma')
    gamma_wrapper.disable()
    return sp.hooks.score(value)