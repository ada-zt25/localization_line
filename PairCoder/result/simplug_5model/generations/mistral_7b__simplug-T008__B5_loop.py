def last_score(value):
    with make_last_score_manager() as (sp, alpha, beta, gamma):
        sp.plugins_context([alpha, beta])
        try:
            result = sp.hooks.score(value)
        finally:
            sp.disable(gamma)
            sp.enable(alpha, beta)
    return result[0]  # Assuming the score hook returns a list with a single scalar value