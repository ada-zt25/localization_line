def beta_only_inside_context_then_all_score(value):
    with sp.plugins_context(["beta"]):
        beta_result = sp.hooks.score(value)
    
    sp.disable("beta")
    all_result = sp.hooks.score(value)

    return beta_result, all_result