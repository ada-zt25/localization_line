def only_beta_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    with sp.plugins_context(["beta"]):
        sp.disable([alpha.name, gamma.name])
        beta_wrapper = sp.get_plugin(beta.name)
        beta_wrapper.enable()
        result = sp.hooks.score(value)
        beta_wrapper.disable()
        sp.enable([alpha.name, gamma.name])
    return result