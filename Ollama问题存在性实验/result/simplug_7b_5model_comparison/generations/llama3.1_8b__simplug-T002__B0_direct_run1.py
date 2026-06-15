def only_alpha_gamma_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.hooks.score.enabled(alpha=True, beta=False, gamma=True) as hook:
        return hook.run(value)