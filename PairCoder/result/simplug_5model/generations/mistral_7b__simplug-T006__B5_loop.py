def disable_alpha_gamma_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context([beta]):
        alpha.wrapper.disable()
        gamma.wrapper.disable()
        result = sp.hooks.score(value)
    return result