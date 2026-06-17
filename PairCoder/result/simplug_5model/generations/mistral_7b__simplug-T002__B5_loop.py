def only_alpha_gamma_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context([alpha, gamma]):
        sp.disable(beta)
        result = sp.hooks.score(value)
        sp.enable(beta)
        return result