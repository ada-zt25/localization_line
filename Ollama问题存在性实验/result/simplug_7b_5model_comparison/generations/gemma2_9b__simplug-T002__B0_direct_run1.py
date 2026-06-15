def only_alpha_gamma_score(value):
  sp.hooks.disable_all()
  sp.hooks.enable(alpha)
  sp.hooks.enable(gamma)
  return sp.hooks.score(value)