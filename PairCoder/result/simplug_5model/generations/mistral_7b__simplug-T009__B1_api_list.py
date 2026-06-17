def disable_alpha_gamma_via_wrappers_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context([beta, gamma]):
        sp.disable(alpha)
        wrapper = sp.get_plugin(alpha)
        wrapper.disable()
        sp.disable(gamma)
        wrapper = sp.get_plugin(gamma)
        wrapper.disable()
        result = sp.hooks.score(value)
    return result