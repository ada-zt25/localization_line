def get_beta_wrapper_disable_then_score(value):
    beta_wrapper = sp.hooks.get('beta')
    if beta_wrapper:
        beta_wrapper.enabled = False
    result = sp.hooks.score(value)
    return result