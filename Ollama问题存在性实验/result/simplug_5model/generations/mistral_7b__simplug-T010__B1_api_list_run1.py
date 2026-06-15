def persistent_disable_beta_then_temp_only_alpha_score(value):
    with sp.plugins_context([alpha]):
        inside = sp.hooks.score(value)
        sp.enable([beta])
        outside = sp.hooks.score(value)
    return inside, outside