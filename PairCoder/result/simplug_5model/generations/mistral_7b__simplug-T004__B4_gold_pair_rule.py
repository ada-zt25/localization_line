def get_beta_wrapper_disable_then_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context([alpha, gamma]):
        wrapper = sp.get_plugin("beta")
        wrapper.disable()
        result = sp.hooks.score(value)
    return result