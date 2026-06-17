def persistent_disable_beta_then_temp_only_alpha_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    
    # Disable beta by name
    sp.disable(beta.name)
    
    with plugins_context([alpha]):
        # Inside the temporary context where only alpha is enabled
        inside_result = sp.hooks.score(value)
        
    # After the context exits
    after_result = sp.hooks.score(value)
    
    return inside_result, after_result