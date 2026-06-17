def first_score(value):
    sp, _, _, _ = make_first_score_manager()

    with sp.plugins_context([plugin for plugin in sp.get_all_plugins()]):
        sp.disable(*[plugin.name for plugin in sp.get_all_plugins() if plugin.name != 'score'])
        sp.enable('score')
        result = sp.hooks.score(value)

    return result