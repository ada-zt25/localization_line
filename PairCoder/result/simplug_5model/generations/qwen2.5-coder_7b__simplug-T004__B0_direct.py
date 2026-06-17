def get_beta_wrapper_disable_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    wrapper = sp.get_plugin_wrapper(beta)
    wrapper.disable()
    return sp.hooks.score(value)