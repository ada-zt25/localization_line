def disable_alpha_gamma_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()

    with plugins_context([alpha, gamma]):
        alpha.wrapper.disable()
        gamma.wrapper.disable()

    result = sp.hooks.score(value)

    alpha.wrapper.enable()
    gamma.wrapper.enable()

    return result