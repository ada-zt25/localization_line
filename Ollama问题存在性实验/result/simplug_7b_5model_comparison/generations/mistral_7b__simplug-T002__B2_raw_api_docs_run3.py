def only_alpha_gamma_score(value):
    with plugins_context([alpha, gamma]):
        sp.hooks.score(value)
        sp.hooks.score(value, disable=[beta])
        results = list(sp.hooks.results())
        original_state = [plugin.enabled for plugin in [alpha, beta, gamma]]
        for plugin in [alpha, gamma]:
            if plugin.enabled:
                plugin.disable()
        result = results[-1]
        for plugin in [alpha, gamma]:
            if not plugin.enabled:
                plugin.enable()
        for plugin in original_state:
            if not plugin:
                plugin.enable()
        return result