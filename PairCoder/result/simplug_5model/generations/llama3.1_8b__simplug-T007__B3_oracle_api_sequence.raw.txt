def first_score(value):
    sp, alpha, beta, gamma = make_first_score_manager()
    return sp.hooks.score(value)