def persistent_disable_beta_then_temp_only_alpha_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    beta.disable()
    with sp.plugins_context([alpha]):
        inside_results = sp.hooks.score(value)
    after_results = sp.hooks.score(value)
    return inside_results, after_results