def beta_only_inside_context_then_all_score(value):
    with sp.plugins_context(["beta"]):
        beta_enabled_result = sp.hooks.score(value)
    
    original_state = sp.get_plugin("alpha").enabled
    sp.disable("beta")
    alpha_enabled_result = sp.hooks.score(value)
    if not original_state:
        sp.enable("alpha")
    
    return beta_enabled_result, alpha_enabled_result