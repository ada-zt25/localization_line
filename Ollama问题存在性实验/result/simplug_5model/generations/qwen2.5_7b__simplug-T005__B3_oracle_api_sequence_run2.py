def beta_only_inside_context_then_all_score(value):
    original_state = sp.plugins_context(alpha=False, beta=True, gamma=False)
    try:
        with original_state:
            inside_beta = sp.hooks.score(value)
    finally:
        outside_beta = sp.hooks.score(value)
    return inside_beta, outside_beta