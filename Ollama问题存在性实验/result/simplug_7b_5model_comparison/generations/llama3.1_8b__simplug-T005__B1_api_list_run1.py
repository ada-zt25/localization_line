def beta_only_inside_context_then_all_score(value):
    with sp.plugins_context([beta]):
        results_beta = sp.hooks.score(value)
    sp.disable(beta.name)
    sp.enable(*[p.name for p in [alpha, gamma]])
    results_all = sp.hooks.score(value)
    return results_beta, results_all