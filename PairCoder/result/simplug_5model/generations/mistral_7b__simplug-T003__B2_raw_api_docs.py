def disable_beta_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with plugins_context([beta]):
        beta.disable()
    result = sp.hooks.score(value)
    return result