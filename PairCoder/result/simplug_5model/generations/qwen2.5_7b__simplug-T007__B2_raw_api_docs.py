def first_score(value):
    sp, alpha, beta, gamma = make_first_score_manager()
    result = sp.hooks.score(value)
    return result