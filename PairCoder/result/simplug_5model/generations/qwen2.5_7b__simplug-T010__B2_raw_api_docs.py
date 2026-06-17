def persistent_disable_beta_then_temp_only_alpha_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    
    # Disable beta by name
    sp.disable('beta')
    
    # Collect score with only alpha enabled temporarily
    with sp.plugins_context([alpha]):
        inside_result = sp.hooks.score(value)
    
    # Re-enable all plugins to their original state
    sp.enable('alpha', 'beta', 'gamma')
    
    # Collect score after the temporary context exits
    after_result = sp.hooks.score(value)
    
    return inside_result, after_result