def disable_beta_then_score(value):
  sp.hooks.disable("beta")
  return sp.hooks.score(value)