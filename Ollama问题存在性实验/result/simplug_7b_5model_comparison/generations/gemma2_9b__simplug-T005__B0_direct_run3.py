def beta_only_inside_context_then_all_score(value):
  with sp.context(beta=True, alpha=False, gamma=False):
    result1 = sp.hooks.score(value)
  result2 = sp.hooks.score(value)
  return result1, result2