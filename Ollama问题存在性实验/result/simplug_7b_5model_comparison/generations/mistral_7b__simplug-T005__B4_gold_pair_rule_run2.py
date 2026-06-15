def beta_only_inside_context_then_all_score(value):
    with sp.plugins_context([beta]):
        result1 = sp.hooks.score(value)
    sp.disable("beta")
    result2 = sp.hooks.score(value)
    return (result1, result2)