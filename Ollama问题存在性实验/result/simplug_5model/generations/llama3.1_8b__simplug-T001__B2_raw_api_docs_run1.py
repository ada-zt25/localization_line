def only_beta_score(value):
    with plugins_context([beta]):
        sp.hooks.score(value)