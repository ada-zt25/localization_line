def only_alpha_gamma_score(value):
  with sp.plugins_context({alpha: alpha, gamma: gamma}):
    return sp.hooks.score(value)