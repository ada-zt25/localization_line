def first_score(value):
    sp, alpha, beta, gamma = make_first_score_manager()
    with sp.plugins_context({'alpha': True, 'beta': False, 'gamma': False}):
        result = sp.hooks.score(value)
    return result