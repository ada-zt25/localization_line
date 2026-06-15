def beta_only_inside_context_then_all_score(value):
    with sp.plugins_context([beta]):
        sp.enable(beta)
        sp.disable(alpha, gamma)
        result1 = sp.hooks.score(value)
    
    sp.enable(alpha, beta, gamma)
    result2 = sp.hooks.score(value)
    return result1, result2