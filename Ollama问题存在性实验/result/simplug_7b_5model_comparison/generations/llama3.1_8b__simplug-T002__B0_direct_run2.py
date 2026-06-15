def only_alpha_gamma_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    result = sp.hooks.score(value)
    with sp.hooks.enabled(alpha=True, beta=False, gamma=True):
        result = sp.hooks.score(value)
    return result