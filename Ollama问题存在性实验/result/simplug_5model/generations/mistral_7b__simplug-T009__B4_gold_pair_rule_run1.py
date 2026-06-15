def disable_alpha_gamma_via_wrappers_then_score(value):
    with sp.plugins_context({'beta': False, 'gamma': False}):
        wrapper_alpha = sp.get_plugin('alpha')
        wrapper_gamma = sp.get_plugin('gamma')
        wrapper_alpha.enable()
        wrapper_gamma.enable()
        result = sp.hooks.score(value)
        wrapper_alpha.disable()
        wrapper_gamma.disable()
    return result