def disable_alpha_gamma_via_wrappers_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()

    alpha_wrapper = next((plugin for plugin in sp.plugins if plugin.name == alpha), None)
    if alpha_wrapper:
        alpha_wrapper.disabled = True

    gamma_wrapper = next((plugin for plugin in sp.plugins if plugin.name == gamma), None)
    if gamma_wrapper:
        gamma_wrapper.disabled = True

    return sp.hooks.score(value)