def disable_alpha_gamma_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    del sp.hooks['alpha']
    del sp.hooks['gamma']
    return sp.hooks.score(value)