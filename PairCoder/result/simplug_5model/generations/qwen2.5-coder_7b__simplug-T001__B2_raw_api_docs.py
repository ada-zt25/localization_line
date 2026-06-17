def only_beta_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with plugins_context((beta,)):
        return sp.hooks.score(value)