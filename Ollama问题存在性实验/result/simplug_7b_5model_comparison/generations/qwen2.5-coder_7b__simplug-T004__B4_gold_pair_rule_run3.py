def get_beta_wrapper_disable_then_score(value):
    wrapper = sp.get_plugin("beta")
    wrapper.disable()
    result = sp.hooks.score(value)
    return result