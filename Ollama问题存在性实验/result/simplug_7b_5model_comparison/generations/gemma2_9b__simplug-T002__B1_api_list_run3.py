def only_alpha_gamma_score(value):
  with sp.plugins_context({'alpha': sp.get_plugin('alpha'), 'gamma': sp.get_plugin('gamma')}):
    sp.disable(*[p for p in sp.plugins if p not in ('alpha', 'gamma')])
    return sp.hooks.score(value)