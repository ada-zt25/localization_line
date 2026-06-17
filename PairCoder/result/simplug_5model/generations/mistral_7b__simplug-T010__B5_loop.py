def persistent_disable_beta_then_temp_only_alpha_score(value):
    sp, alpha, beta, gamma = make_score_manager()

    beta_wrapper = sp.get_plugin(beta)
    beta_wrapper.disable()

    with sp.plugins_context([alpha]):
        inside_result = sp.hooks.score(value)

    outside_result = sp.hooks.score(value)

    return inside_result, outside_result