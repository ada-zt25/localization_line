def beta_only_inside_context_then_all_score(value):
    original_state = sp.hooks.get_enabled_plugins()
    sp.hooks.enable_plugin(beta)
    with sp.hooks.context():
        beta_result = sp.hooks.score(value)
    sp.hooks.set_enabled_plugins(original_state)
    all_result = sp.hooks.score(value)
    return beta_result, all_result