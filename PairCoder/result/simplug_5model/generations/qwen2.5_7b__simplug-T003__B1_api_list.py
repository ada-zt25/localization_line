def disable_beta_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context(plugins=[alpha, gamma]):
        sp.disable('beta')
        result = sp.hooks.score(value)
    return result