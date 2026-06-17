def get_beta_wrapper_disable_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    wrapper = beta.get_plugin()
    wrapper.disable()
    result = sp.hooks.score(value)
    return result