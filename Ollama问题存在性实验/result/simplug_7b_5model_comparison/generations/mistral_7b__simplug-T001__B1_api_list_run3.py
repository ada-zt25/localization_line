def only_beta_score(value):
    with sp.plugins_context([beta]):
        sp.disable(*[alpha, gamma])
        result = sp.hooks.score(value)
        beta.enable()
        return result