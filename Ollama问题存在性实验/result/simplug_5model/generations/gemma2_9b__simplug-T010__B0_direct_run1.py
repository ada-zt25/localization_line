def persistent_disable_beta_then_temp_only_alpha_score(value):
  sp.disable_hook("beta")
  with sp.temporary_context({"alpha": True}):
    inside = sp.hooks.score(value)
  after = sp.hooks.score(value)
  return inside, after