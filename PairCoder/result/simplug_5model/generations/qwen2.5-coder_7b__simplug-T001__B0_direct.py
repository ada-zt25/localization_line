def only_beta_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.hooks.score.use(beta):
        return sp.hooks.score(value)