def beta_only_inside_context_then_all_score(value):
    with sp.plugins_context({'beta': True}):
        score1 = sp.hooks.score(value)
    sp.plugins_context.clear()
    score2 = sp.hooks.score(value)
    return score1, score2