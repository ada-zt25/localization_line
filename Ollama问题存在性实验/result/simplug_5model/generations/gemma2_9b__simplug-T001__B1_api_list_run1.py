def only_beta_score(value):
  with sp.plugins_context([sp.get_plugin('beta')]):
    return sp.hooks.score(value)