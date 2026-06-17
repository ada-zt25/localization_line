def persistent_disable_beta_then_temp_only_alpha_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    original_plugins = list(sp.get_plugins())

    # Disable beta
    beta_wrapper = get_plugin(beta)
    beta_wrapper.disable()

    # Collect score before disabling beta
    inside_results = hooks.score(value)

    # Create temporary context for only alpha
    sp.plugins_context([alpha])

    # Collect score within the temporary context
    temp_results = hooks.score(value)

    # Restore original plugins state
    sp.plugins_context(original_plugins)

    # Collect score after restoring original plugins state
    after_results = hooks.score(value)

    return inside_results, after_results