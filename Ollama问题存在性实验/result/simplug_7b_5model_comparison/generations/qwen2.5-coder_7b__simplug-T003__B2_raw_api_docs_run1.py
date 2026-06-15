def disable_beta_then_score(value):
    with sp.plugins_context([beta]):
        beta.disable()
        return sp.hooks.score(value)