def disable_alpha_gamma_then_score(value):
  sp.disable('alpha', 'gamma')
  return sp.hooks.score(value)