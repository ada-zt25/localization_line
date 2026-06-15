def beta_only_inside_context_then_all_score(value):
  with sp.plugins_context([sp.get_plugin('beta')]):
    beta_only_scores = sp.hooks.score(value)
  all_scores = sp.hooks.score(value)
  return beta_only_scores, all_scores