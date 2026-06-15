def get_beta_wrapper_disable_then_score(value):
    beta_plugin = gamma.get(beta)
    if beta_plugin:
        beta_plugin.disable()
    return sp.hooks.score(value)