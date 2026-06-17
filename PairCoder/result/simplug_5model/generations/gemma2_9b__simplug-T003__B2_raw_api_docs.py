def disable_beta_then_score(value):
  sp, alpha, beta, gamma = make_score_manager()
  sp.disable('beta')
  return sp.hooks.score(value)