def beta_only_inside_context_then_all_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    original_plugins_state = sp.plugins.copy()
    
    with sp.plugins_context(beta):
        beta_result = sp.hooks.score(value)
    
    sp.plugins = original_plugins_state
    all_result = sp.hooks.score(value)
    
    return beta_result, all_result