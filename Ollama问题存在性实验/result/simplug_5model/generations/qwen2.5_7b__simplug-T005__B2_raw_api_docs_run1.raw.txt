def beta_only_inside_context_then_all_score(value):
    with sp.plugins_context(beta):
        temp_result = sp.hooks.score(value)
    
    original_state = [p.name for p in (alpha, beta, gamma) if p.enabled]
    sp.enable('beta')
    all_results = sp.hooks.score(value)
    sp.disable('beta')
    for name in original_state:
        sp.enable(name)
    
    return temp_result, all_results