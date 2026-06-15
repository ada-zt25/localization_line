def beta_only_inside_context_then_all_score(value):
    original_state = sp.get_plugin('beta').get_state()
    with plugins_context(['beta']):
        beta_enabled_result = sp.hooks.score(value)
    sp.get_plugin('beta').set_state(original_state)
    all_plugins_enabled_result = sp.hooks.score(value)
    return beta_enabled_result, all_plugins_enabled_result