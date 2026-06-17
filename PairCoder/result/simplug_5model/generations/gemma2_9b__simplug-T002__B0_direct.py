def only_alpha_gamma_score(value):
  sp, alpha, beta, gamma = make_score_manager()
  sp.hooks.score(value, enabled=[alpha, gamma])
  return sp.hooks.score.result