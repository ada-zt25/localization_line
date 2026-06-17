def last_score(value):
    sp, _, _, _ = make_last_score_manager()
    with sp.plugins_context([sp.get_plugin('first'), sp.get_plugin('middle'), sp.get_plugin('other')]):
        sp.disable('first')
        sp.enable('last')
        result = sp.hooks.score(value)
        sp.disable('last')
        sp.enable('first')
    return result