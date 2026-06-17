def last_score(value):
    sp, alpha, beta, gamma = make_last_score_manager()
    with plugins_context([alpha, beta, gamma]):
        sp.hooks.score(value)
        return value