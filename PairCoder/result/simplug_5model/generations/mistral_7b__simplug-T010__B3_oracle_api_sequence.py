def persistent_disable_beta_then_temp_only_alpha_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    inside_result, after_result = None, None

    # Disable beta
    sp.disable(beta)

    # Create a temporary context where only alpha is enabled
    with sp.plugins_context([alpha]):
        inside_result = sp.hooks.score(value)

    # Exit the temporary context and collect the score again
    after_result = sp.hooks.score(value)

    return inside_result, after_result