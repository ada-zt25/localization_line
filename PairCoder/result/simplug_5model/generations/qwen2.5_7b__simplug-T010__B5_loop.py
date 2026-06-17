def persistent_disable_beta_then_temp_only_alpha_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    
    # Disable beta by name
    beta.disable()

    # Collect score with only alpha enabled temporarily
    with sp.plugins_context(plugins=(alpha,)):
        first_result = sp.hooks.score(value)

    # Re-enable the plugins to their original state
    alpha.enable()
    beta.enable()

    # Collect score again after the context exits
    second_result = sp.hooks.score(value)
    
    return first_result, second_result