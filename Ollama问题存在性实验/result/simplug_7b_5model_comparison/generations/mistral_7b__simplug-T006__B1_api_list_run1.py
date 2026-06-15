def disable_alpha_gamma_then_score(value):
    with sp.plugins_context([beta]):
        alpha.disable()
        gamma.disable()
        result = sp.hooks.score(value)
        alpha.enable()
        gamma.enable()
        return result