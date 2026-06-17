def beta_only_inside_context_then_all_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    
    with sp.plugins_context(plugins=[beta]):
        inside_beta = [hook for hook in sp.hooks.score(value)]
    
    all_plugins = [hook for hook in sp.hooks.score(value)]
    
    return inside_beta, all_plugins