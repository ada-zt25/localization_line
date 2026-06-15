def only_beta_score(value):
    with plugins_context([beta]):
        sp.disable(*[plugin for plugin in [alpha, gamma] if plugin])
        sp.enable(beta)
        result = hooks.score(value)
        return result[0] if len(result) > 0 else None