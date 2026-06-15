def only_alpha_gamma_score(value):
    with sp.plugins_context(["alpha", "gamma"]):
        wrapper_alpha = sp.get_plugin(alpha)
        wrapper_gamma = sp.get_plugin(gamma)

        wrapper_alpha.disable()
        wrapper_gamma.disable()

        sp.hooks.score(value)

        wrapper_alpha.enable()
        wrapper_gamma.enable()

        sp.hooks.score(value)

    result = sp.hooks.score(value)
    return result