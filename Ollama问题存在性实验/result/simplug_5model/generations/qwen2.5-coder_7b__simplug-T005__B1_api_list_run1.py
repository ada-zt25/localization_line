def beta_only_inside_context_then_all_score(value):
    with sp.plugins_context(plugins=[beta]):
        result_beta_enabled = sp.hooks.score(value)
    
    original_plugins_state = [sp.get_plugin(name) for name in sp.enabled_plugins]
    for plugin in original_plugins_state:
        plugin.enable()
    
    result_all_enabled = sp.hooks.score(value)
    
    return result_beta_enabled, result_all_enabled