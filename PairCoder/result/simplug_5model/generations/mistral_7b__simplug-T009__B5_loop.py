def disable_alpha_gamma_via_wrappers_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context([beta.name, gamma.name]):
        beta_wrapper = sp.get_plugin(beta.name)
        beta_wrapper.disable()
        gamma_wrapper = sp.get_plugin(gamma.name)
        gamma_wrapper.disable()
        result = sp.hooks.score(value)
    return result