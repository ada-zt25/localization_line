def disable_alpha_gamma_via_wrappers_then_score(value):
    with sp.plugins_context({'alpha', 'gamma'}):
        alpha_wrapper = sp.get_plugin('alpha')
        alpha_wrapper.disable()
        gamma_wrapper = sp.get_plugin('gamma')
        gamma_wrapper.disable()
        results = sp.hooks.score(value)
    return results