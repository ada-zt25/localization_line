def only_beta_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context(disable=[alpha, gamma]):
        return sp.hooks.score(value)