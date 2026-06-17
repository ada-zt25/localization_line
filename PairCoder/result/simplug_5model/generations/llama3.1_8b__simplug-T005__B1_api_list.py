def beta_only_inside_context_then_all_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context([beta]):
        result_inside_context = sp.hooks.score(value)
    sp.disable(beta.name).enable(alpha.name).enable(gamma.name)
    result_outside_context = sp.hooks.score(value)
    return result_inside_context, result_outside_context