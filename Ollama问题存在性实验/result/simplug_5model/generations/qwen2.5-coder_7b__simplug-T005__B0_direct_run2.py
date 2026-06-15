def beta_only_inside_context_then_all_score(value):
    original_state = sp.hooks.get_enabled_plugins()
    try:
        sp.hooks.enable_plugin(beta)
        with sp.hooks.context():
            result_with_beta = sp.hooks.score(value)
    finally:
        sp.hooks.set_enabled_plugins(original_state)
        result_with_original = sp.hooks.score(value)
    return result_with_beta, result_with_original