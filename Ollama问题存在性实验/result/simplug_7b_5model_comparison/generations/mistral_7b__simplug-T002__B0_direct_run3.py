def only_alpha_gamma_score(value):
    sp.hooks.enable('alpha')
    sp.hooks.enable('gamma')
    sp.hooks.disable('beta')
    score = sp.hooks.score(value)
    sp.hooks.enable('beta')  # enable beta after scoring to ensure it's not affected by the temporary disable
    return score