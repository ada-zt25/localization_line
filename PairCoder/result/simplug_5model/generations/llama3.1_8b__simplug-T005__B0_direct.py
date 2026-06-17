def beta_only_inside_context_then_all_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.hooks.enable_plugin(beta):
        score_with_beta_enabled = sp.hooks.score(value)
    score_with_all_plugins_enabled = sp.hooks.score(value)
    return score_with_beta_enabled, score_with_all_plugins_enabled