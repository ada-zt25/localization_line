def only_alpha_gamma_score(value):
    with plugins_context([alpha, gamma]):
        disable('beta')
        return sp.hooks.score(value)