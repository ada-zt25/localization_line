def beta_only_inside_context_then_all_score(value):
    with sp.plugins_context(["beta"]):
        beta_enabled_result = sp.hooks.score(value)
    
    original_state = sp.get_plugin("beta").enabled
    sp.disable("beta")
    all_plugins_disabled_result = sp.hooks.score(value)
    if not original_state:
        sp.enable("beta")
    
    return beta_enabled_result, all_plugins_disabled_result