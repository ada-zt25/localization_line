def only_beta_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context([beta]):
        sp.disable(alpha)
        sp.disable(gamma)
        sp.hooks.score(value)
        result = next(sp.hooks['score'])
    sp.enable(alpha)
    sp.enable(gamma)
    return result