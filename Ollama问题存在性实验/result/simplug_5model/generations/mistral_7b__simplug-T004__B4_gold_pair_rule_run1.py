def get_beta_wrapper_disable_then_score(value):
    with sp.plugins_context([alpha, gamma]):
        wrapper = sp.get_plugin("beta")
        wrapper.disable()
        return sp.hooks.score(value)