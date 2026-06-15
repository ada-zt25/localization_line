def beta_only_inside_context_then_all_score(value):
    with sp.plugins_context(beta):
        temp_result = sp.hooks.score(value)
    
    original_state_result = sp.hooks.score(value)
    
    return temp_result, original_state_result