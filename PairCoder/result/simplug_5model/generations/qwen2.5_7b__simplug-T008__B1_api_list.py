def last_score(value):
    sp, alpha, beta, gamma = make_last_score_manager()
    with sp.plugins_context([alpha, beta, gamma]):
        return sp.hooks.score(value)