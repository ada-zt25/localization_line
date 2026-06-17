def beta_only_inside_context_then_all_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    
    with sp.only(beta):
        beta_result = sp.hooks.score(value)
    
    all_result = sp.hooks.score(value)
    
    return beta_result, all_result