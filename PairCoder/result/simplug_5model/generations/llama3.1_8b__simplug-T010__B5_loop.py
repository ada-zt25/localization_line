def persistent_disable_beta_then_temp_only_alpha_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    beta.disable()  # disable beta by name
    with sp.plugins_context([alpha]):  # temporary context where only alpha is enabled
        inside_result = sp.hooks.score(value)
    after_result = sp.hooks.score(value)  # collect score hook result again after the context exits
    return inside_result, after_result