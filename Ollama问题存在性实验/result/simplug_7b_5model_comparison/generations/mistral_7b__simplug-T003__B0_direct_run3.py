def disable_beta_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    del sp.plugins[beta.__name__]
    return sp.hooks.score(value)