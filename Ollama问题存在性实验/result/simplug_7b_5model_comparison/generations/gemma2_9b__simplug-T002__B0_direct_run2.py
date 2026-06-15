def only_alpha_gamma_score(value):
  sp.hooks.set_active_scores({'alpha': True, 'gamma': True})
  result = sp.hooks.score(value)
  sp.hooks.set_active_scores({'alpha': alpha, 'beta': beta, 'gamma': gamma})
  return result