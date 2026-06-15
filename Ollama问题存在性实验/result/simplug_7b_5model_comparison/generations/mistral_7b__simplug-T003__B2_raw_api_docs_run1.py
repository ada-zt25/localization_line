def disable_beta_then_score(value):
    with plugins_context([beta]):
        beta.wrapper.disable()
        result = sp.hooks.score(value)
    beta.wrapper.enable()
    return result