def beta_only_inside_context_then_all_score(value):
    original_state = sp.plugins_context()
    
    with sp.plugins_context(beta=True, alpha=False, gamma=False, sp.default_plugin_state()):
        beta_result = sp.hooks.score(value)
    
    all_scores_result = sp.hooks.score(value)
    
    return beta_result, all_scores_result