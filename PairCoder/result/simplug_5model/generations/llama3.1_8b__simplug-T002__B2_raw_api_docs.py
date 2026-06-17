def only_alpha_gamma_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with plugins_context([alpha, gamma]):
        disable('beta')
        result = sp.hooks.score(value)
    return result