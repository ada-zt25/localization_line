def disable_beta_then_score(value):
    with plugins_context([beta]):
        sp.disable(beta.name)
        return sp.hooks.score(value)