def beta_only_inside_context_then_all_score(value):
    with sp.hooks.temporarily_enable(beta=True, alpha=False, gamma=False):
        temp_result = sp.hooks.score(value)
    
    original_result = sp.hooks.score(value)
    
    return temp_result, original_result