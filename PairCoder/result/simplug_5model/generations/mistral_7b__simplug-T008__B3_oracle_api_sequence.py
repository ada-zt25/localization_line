def last_score(value):
    sp, alpha, beta, gamma = make_last_score_manager()
    return sp.hooks.score(value)