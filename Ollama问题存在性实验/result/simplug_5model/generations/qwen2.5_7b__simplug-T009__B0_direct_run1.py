def disable_alpha_gamma_via_wrappers_then_score(value):
    alpha_wrapper = sp.plugins['alpha'].wrapper
    gamma_wrapper = sp.plugins['gamma'].wrapper
    alpha_wrapper.disable()
    gamma_wrapper.disable()
    return sp.hooks.score(value)