def beta_only_inside_context_then_all_score(value):
    sp, alpha, beta, gamma = make_score_manager()

    with sp.plugins_context([beta]):
        sp.disable(alpha.name)
        result1 = sp.hooks.score(value)
        sp.enable(alpha.name)

        sp.disable(beta.name)
        result2 = sp.hooks.score(value)
        sp.enable(beta.name)

    return result1, result2