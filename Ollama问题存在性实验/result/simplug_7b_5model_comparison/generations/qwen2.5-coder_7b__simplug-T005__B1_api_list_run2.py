def beta_only_inside_context_then_all_score(value):
    with sp.plugins_context(plugins=[beta]):
        beta_enabled_result = sp.hooks.score(value)
    
    original_plugins = [sp.get_plugin(name) for name in sp.enabled]
    for plugin in original_plugins:
        plugin.disable()
    
    all_disabled_result = sp.hooks.score(value)
    
    for plugin in original_plugins:
        plugin.enable()
    
    return beta_enabled_result, all_disabled_result