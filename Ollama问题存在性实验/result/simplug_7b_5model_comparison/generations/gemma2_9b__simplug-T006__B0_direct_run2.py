def disable_alpha_gamma_then_score(value):
  sp.hooks.disable("alpha")
  sp.hooks.disable("gamma")
  return sp.hooks.score(value)