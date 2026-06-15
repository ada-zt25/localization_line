def get_beta_wrapper_disable_then_score(value):
    beta_wrapper = get_plugin('beta')
    with plugins_context([beta]):
        beta_wrapper.disable()
        result = sp.hooks.score(value)
    return result