def persistent_disable_beta_then_temp_only_alpha_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins(beta).disabled():
        inside_value = sp.hooks.score(value)
        with sp.plugins(alpha).enabled(), sp.plugins(beta, gamma).disabled():
            temp_value = sp.hooks.score(value)
    after_value = sp.hooks.score(value)
    return inside_value, after_value