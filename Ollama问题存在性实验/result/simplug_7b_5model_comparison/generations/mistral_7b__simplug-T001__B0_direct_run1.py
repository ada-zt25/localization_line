def only_beta_score(value):
    sp.hooks.enable('beta')
    score = sp.hooks.score(value)
    sp.hooks.disable('beta')
    return score