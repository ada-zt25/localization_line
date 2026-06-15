def only_alpha_gamma_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    original_hooks = sp.hooks.score.hooks
    sp.hooks.score.hooks = {'alpha': True, 'gamma': True}
    result = sp.hooks.score(value)
    sp.hooks.score.hooks = original_hooks
    return result