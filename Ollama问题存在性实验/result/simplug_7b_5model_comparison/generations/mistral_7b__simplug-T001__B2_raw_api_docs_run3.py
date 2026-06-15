def only_beta_score(value):
    with plugins_context([beta]):
        sp.hooks.score(value)
        beta_wrapper = get_plugin(beta)
        beta_wrapper.enable()
        result = hooks.score(value)
        beta_wrapper.disable()
    return result