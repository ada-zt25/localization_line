def get_beta_wrapper_disable_then_score(value):
    beta = alpha.get_plugin(beta)
    wrapper = beta.plugin
    wrapper.disable()
    return sp.hooks.score(value)