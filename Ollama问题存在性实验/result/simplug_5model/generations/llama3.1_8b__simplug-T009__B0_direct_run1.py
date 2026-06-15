def disable_alpha_gamma_via_wrappers_then_score(value):
    alpha_wrapper = sp.hooks.get_plugin_wrapper(alpha)
    gamma_wrapper = sp.hooks.get_plugin_wrapper(gamma)
    alpha_wrapper.disable()
    gamma_wrapper.disable()
    return sp.hooks.score(value)