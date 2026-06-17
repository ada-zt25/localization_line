def only_beta_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with plugins_context([beta]):
        disable('alpha', 'gamma')
        result = sp.hooks.score(value)
    return result