def beta_only_inside_context_then_all_score(value):
    with make_first_score_manager() as (sp, alpha, beta, gamma):
        sp.hooks.score.disable(alpha)
        sp.hooks.score.enable(beta)
        result1 = sp.hooks.score(value)
        sp.hooks.score.disable(beta)
        sp.hooks.score.enable(gamma)
        result2 = sp.hooks.score(value)
        return (result1, result2)