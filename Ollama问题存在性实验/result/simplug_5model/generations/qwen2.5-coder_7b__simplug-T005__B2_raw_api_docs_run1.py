def beta_only_inside_context_then_all_score(value):
    original_state = sp.get_plugin('beta').enabled
    with plugins_context(['beta']):
        beta_result = sp.hooks.score(value)
    sp.get_plugin('beta').enabled = original_state
    all_scores = sp.hooks.score(value)
    return beta_result, all_scores