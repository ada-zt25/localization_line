def persistent_disable_beta_then_temp_only_alpha_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    sp.disable('beta')
    
    with plugins_context([alpha]):
        inside_result = sp.hooks.score(value)
    
    after_result = sp.hooks.score(value)
    
    return inside_result, after_result