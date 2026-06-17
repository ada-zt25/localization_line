from simplug import Simplug

def first_score(value):
    sp, _, _, _ = make_first_score_manager()
    with sp.plugins_context([sp.get_plugin('alpha'), sp.get_plugin('beta'), sp.get_plugin('gamma')]):
        sp.enable('alpha', 'beta', 'gamma')
        sp.hooks.score(value)
        results = sp.hooks.results()
    sp.disable('alpha', 'beta', 'gamma')
    return results[0] if results else None