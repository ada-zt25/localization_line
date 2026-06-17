def first_score(value):
    sp, _, _, _ = make_first_score_manager()
    return sp.hooks.score(value)