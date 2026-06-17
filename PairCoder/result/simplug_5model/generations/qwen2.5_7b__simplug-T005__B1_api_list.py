def beta_only_inside_context_then_all_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    
    with sp.plugins_context(plugins=[beta]):
        result_beta_inside = sp.hooks.score(value)
    
    result_all_plugins = sp.hooks.score(value)
    
    return result_beta_inside, result_all_plugins