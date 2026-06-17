def beta_only_inside_context_then_all_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    
    original_state = [alpha.enabled, beta.enabled, gamma.enabled]
    
    with plugins_context([beta]):
        beta_enabled_result = sp.hooks.score(value)
    
    for plugin, enabled in zip([alpha, beta, gamma], original_state):
        if enabled:
            plugin.enable()
        else:
            plugin.disable()
    
    all_plugins_result = sp.hooks.score(value)
    
    return beta_enabled_result, all_plugins_result