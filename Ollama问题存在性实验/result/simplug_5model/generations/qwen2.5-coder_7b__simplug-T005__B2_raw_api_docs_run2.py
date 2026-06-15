def beta_only_inside_context_then_all_score(value):
    with sp.plugins_context([beta]):
        beta_enabled_result = sp.hooks.score(value)
    original_state = [p.enabled for p in (alpha, beta, gamma)]
    for p in (alpha, gamma):
        p.disable()
    all_scores_result = sp.hooks.score(value)
    for i, p in enumerate((alpha, gamma)):
        if original_state[i]:
            p.enable()
    return beta_enabled_result, all_scores_result