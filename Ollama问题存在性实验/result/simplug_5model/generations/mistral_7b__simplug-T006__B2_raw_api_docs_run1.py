def disable_alpha_gamma_then_score(value):
    with plugins_context([alpha, gamma]):
        alpha.wrapper.disable()
        gamma.wrapper.disable()
        results = sp.hooks.score(value)
    return results