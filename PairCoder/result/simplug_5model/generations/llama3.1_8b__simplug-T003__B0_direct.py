def disable_beta_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    beta.disable_by_name('beta')
    return sp.hooks.score(value)