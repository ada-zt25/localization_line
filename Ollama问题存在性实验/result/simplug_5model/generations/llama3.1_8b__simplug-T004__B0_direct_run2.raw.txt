def get_beta_wrapper_disable_then_score(value):
    beta_wrapper = sp.hooks.get_plugin(beta)
    beta_wrapper.disable()
    return sp.hooks.score(value)