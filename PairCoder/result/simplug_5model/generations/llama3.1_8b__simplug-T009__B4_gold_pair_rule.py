def disable_alpha_gamma_via_wrappers_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context([alpha, gamma]):
        pass
    wrapper = sp.get_plugin("alpha")
    wrapper.disable()
    wrapper = sp.get_plugin("gamma")
    wrapper.disable()
    return sp.hooks.score(value)