def beta_only_inside_context_then_all_score(value):
    with sp.hooks.temporary_override({'beta': True, 'gamma': False}):
        score1 = sp.hooks.score(value)

    sp.hooks.restore()
    score2 = sp.hooks.score(value)

    return score1, score2