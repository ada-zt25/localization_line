def only_alpha_gamma_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins.temporarily_enabled(['alpha', 'gamma']):
        return sp.hooks.score(value)