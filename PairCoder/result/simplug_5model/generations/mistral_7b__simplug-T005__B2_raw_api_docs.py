def beta_only_inside_context_then_all_score(value):
    sp, alpha, beta, gamma = make_score_manager()

    with plugins_context([beta.name]):
        beta.disable()
        beta.enable()
        sp.hooks.score(value)
        beta_results = sp.hooks.score(value, result=SimplugResult.FIRST)

    beta.disable()
    beta.enable()
    all_results = sp.hooks.score(value, result=SimplugResult.ALL_AVAILS)

    return beta_results, all_results