def beta_only_inside_context_then_all_score(value):
    with sp.plugins_context([beta.name]):
        result1 = sp.hooks.score(value)
    sp.disable(beta.name)
    result2 = sp.hooks.score(value)
    sp.enable(beta.name)
    return result1, result2