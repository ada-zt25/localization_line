from simplug import with_plugins_disabled, with_plugins_enabled

def persistent_disable_beta_then_temp_only_alpha_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    
    # Disable beta by name
    sp.hooks.score.plugins.remove(beta)
    
    # Temporarily enable only alpha and collect score inside context
    with with_plugins_enabled([alpha]):
        inside_result = sp.hooks.score(value)
        
    # Collect score after context exits
    after_result = sp.hooks.score(value)
    
    return (inside_result, after_result)