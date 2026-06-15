def beta_only_inside_context_then_all_score(value):
    with sp.hooks.enable('beta'):
        score1 = sp.hooks.score(value)
    sp.hooks.disable('beta')
    score2 = sp.hooks.score(value)
    return score1, score2