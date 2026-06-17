def beta_only_inside_context_then_all_score(value):
    sp, alpha, beta, gamma = make_score_manager()
    
    with sp.plugins_context((beta,)):
        result_with_beta = sp.hooks.score(value)
    
    original_plugins_state = [sp.get_plugin(name) for name in (alpha, beta, gamma)]
    for plugin in original_plugins_state:
        plugin.enable()
    
    result_with_all = sp.hooks.score(value)
    
    return result_with_beta, result_with_all