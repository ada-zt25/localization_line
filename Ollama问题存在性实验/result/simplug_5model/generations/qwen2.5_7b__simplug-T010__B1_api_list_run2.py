def persistent_disable_beta_then_temp_only_alpha_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    
    # Disable beta by name
    sp.disable(beta.name)
    
    # Collect score with only alpha enabled temporarily
    with sp.plugins_context([alpha]):
        inside_result = sp.hooks.score(value)
    
    # Collect score after context exits (beta is still disabled)
    after_result = sp.hooks.score(value)
    
    return inside_result, after_result