def get_beta_wrapper_disable_then_score(value):
    with plugins_context(beta.get_plugin('score')):
        beta.get_plugin('score').disable()
        return sp.hooks.score(value)