def only_beta_score(value):
    wrapper = sp.get_plugin("beta")
    wrapper.disable()
    with sp.plugins_context(["beta"]):
        result = sp.hooks.score(value)
    return result