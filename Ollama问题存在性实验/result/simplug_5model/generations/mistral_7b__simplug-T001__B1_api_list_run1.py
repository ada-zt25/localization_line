def only_beta_score(value):
    with sp.plugins_context([beta]):
        sp.disable(*[plugin for plugin in [sp.get_plugin(name) for name in [alpha, gamma]]])
        result = sp.hooks.score(value)
        sp.enable(*[plugin.enable() for plugin in [sp.get_plugin(name) for name in [alpha, gamma]]])
        return result[beta.name]