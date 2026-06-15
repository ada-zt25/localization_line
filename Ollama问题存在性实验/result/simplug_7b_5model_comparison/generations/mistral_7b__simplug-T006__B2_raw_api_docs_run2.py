def disable_alpha_gamma_then_score(value):
    with plugins_context([alpha, gamma]):
        alpha.wrapper.disable()
        gamma.wrapper.disable()
        result = sp.hooks.score(value)
    return result