def get_beta_wrapper_disable_then_score(value):
  sp, alpha, beta, gamma = make_score_manager()
  with sp.plugins_context([alpha, gamma]):
    beta_wrapper = sp.get_plugin('beta')
    beta_wrapper.disable()
    return sp.hooks.score(value)