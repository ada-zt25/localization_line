def persistent_disable_beta_then_temp_only_alpha_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    sp.plugins[beta.name].disable()
    
    inside_value = None
    after_value = None
    
    with sp.plugins_context([alpha]):
        inside_value = sp.hooks.score(value)
    
    after_value = sp.hooks.score(value)
    
    return inside_value, after_value