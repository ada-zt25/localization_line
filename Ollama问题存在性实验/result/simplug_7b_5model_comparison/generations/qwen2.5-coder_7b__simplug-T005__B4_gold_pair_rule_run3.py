def beta_only_inside_context_then_all_score(value):
    with sp.plugins_context(["beta"]):
        beta_enabled_result = sp.hooks.score(value)
    
    original_state = sp.get_plugin("alpha").enabled, sp.get_plugin("gamma").enabled
    sp.disable("alpha")
    sp.disable("gamma")
    all_disabled_result = sp.hooks.score(value)
    
    sp.get_plugin("alpha").enable()
    sp.get_plugin("gamma").enable()
    
    return beta_enabled_result, all_disabled_result