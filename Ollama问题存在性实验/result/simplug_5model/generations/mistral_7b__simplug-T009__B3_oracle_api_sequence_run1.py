def disable_alpha_gamma_via_wrappers_then_score(value):
    alpha_wrapper = sp.get_plugin('alpha')
    alpha_wrapper.disable()

    gamma_wrapper = sp.get_plugin('gamma')
    gamma_wrapper.disable()

    return sp.hooks.score(value)