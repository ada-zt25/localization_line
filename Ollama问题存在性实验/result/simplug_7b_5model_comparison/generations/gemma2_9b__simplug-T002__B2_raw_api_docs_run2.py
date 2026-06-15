def only_alpha_gamma_score(value):
  with plugins_context([alpha, gamma]):
    sp.hooks.score(value)