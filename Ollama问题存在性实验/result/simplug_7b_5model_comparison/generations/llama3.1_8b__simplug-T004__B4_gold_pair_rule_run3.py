def get_beta_wrapper_disable_then_score(value):
    global sp, alpha, beta, gamma
    wrapper = beta.get_plugin()
    wrapper.disable()
    return sp.hooks.score(value)