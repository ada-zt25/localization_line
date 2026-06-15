def beta_only_inside_context_then_all_score(value):
  with plugins_context([beta]):
    beta_only_result = sp.hooks.score(value)
  all_plugins_result = sp.hooks.score(value)
  return beta_only_result, all_plugins_result