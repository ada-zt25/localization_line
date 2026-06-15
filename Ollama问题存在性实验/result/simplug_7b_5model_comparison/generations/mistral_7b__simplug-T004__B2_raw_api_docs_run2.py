def get_beta_wrapper_disable_then_score(value):
    beta_wrapper = get_plugin('beta')
    plugins_context([beta])
    beta_wrapper.disable()
    result = sp.hooks.score(value)
    plugins_context.pop()
    beta_wrapper.enable()
    return result