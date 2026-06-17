def persistent_disable_beta_then_temp_only_alpha_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with simplug.ContextManager(sp, [gamma]):  # disable beta and enable gamma temporarily
        inside_result = sp.hooks.score(value)
    sp.plugins[beta].enabled = True  # re-enable beta
    with simplug.ContextManager(sp, [alpha]):  # disable everything except alpha
        after_result = sp.hooks.score(value)
    return inside_result, after_result