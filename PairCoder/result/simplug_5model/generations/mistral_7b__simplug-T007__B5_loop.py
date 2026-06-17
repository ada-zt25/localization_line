def first_score(value):
    with make_first_score_manager() as (sp, _, _, _):
        sp.disable('first')
        sp.enable('second')
        result = sp.hooks.score(value)
        sp.plugins_context([('first', True), ('second', False)])
        first_result = sp.get_plugin('first').result
        return first_result