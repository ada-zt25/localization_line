def disable_alpha_gamma_then_score(value):
  sp, alpha, beta, gamma = make_score_manager()
  sp.disable_plugin('alpha')
  sp.disable_plugin('gamma')
  return sp.hooks.score(value)