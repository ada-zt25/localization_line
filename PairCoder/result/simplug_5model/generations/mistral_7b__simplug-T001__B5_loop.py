def only_beta_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context([beta]):
        sp.disable(alpha)
        sp.disable(gamma)
        result = sp.hooks.score(value)
        sp.enable(alpha)
        sp.enable(gamma)
        return result[beta.name]