def last_score(value):
    with sp.plugins_context([sp.get_plugin('score')]):
        sp.disable(['last_score'])
        sp.hooks.score(value)
        result = sp.hooks.score(result=LAST).pop()
        sp.enable(['last_score'])
    return result