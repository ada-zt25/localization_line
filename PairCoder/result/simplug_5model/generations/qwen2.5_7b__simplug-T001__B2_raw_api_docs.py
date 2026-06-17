def only_beta_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context([beta]):
        sp.hooks.score(value)