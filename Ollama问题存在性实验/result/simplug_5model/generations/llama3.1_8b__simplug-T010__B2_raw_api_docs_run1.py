def persistent_disable_beta_then_temp_only_alpha_score(value):
    with plugins_context([alpha]):
        disable(beta)
        inside = sp.hooks.score(value)
    after = sp.hooks.score(value)
    return inside, after