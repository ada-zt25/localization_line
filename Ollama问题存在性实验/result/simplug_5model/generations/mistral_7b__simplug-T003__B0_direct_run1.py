def disable_beta_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    beta.disabled = True
    return sp.hooks.score(value)