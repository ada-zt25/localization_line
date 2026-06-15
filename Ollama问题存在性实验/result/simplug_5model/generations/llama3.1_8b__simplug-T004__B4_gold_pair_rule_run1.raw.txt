def get_beta_wrapper_disable_then_score(value):
    with sp.plugins_context([beta]):
        beta.disable()
        return sp.hooks.score(value)