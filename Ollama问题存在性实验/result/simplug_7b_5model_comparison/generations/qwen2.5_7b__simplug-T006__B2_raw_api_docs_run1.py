def disable_alpha_gamma_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    sp.disable('alpha', 'gamma')
    with sp.hooks.score(value):
        pass
    return value