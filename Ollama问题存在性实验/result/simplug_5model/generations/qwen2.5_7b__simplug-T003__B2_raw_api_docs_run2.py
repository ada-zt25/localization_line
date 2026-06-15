def disable_beta_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    sp.hooks.disable('beta')
    result = sp.hooks.score(value)
    return result