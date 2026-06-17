def only_alpha_gamma_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context(disable=[beta]):
        return sp.hooks.score(value)