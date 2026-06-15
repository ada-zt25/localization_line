def disable_alpha_gamma_via_wrappers_then_score(value):
    with sp.plugins_context([alpha, gamma]):
        alpha.disable()
        gamma.disable()
    return sp.hooks.score(value)