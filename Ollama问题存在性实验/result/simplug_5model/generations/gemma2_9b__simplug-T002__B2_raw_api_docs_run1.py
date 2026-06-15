def only_alpha_gamma_score(value):
  sp.disable('beta')
  with plugins_context([alpha, gamma]):
    return sp.hooks.score(value)