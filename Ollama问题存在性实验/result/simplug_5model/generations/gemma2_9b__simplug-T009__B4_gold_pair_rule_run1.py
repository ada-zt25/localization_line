def disable_alpha_gamma_via_wrappers_then_score(value):
  sp.disable("alpha", "gamma")
  with sp.plugins_context({"alpha": sp.get_plugin("alpha"), "gamma": sp.get_plugin("gamma")}):
    alpha_wrapper = sp.get_plugin("alpha")
    gamma_wrapper = sp.get_plugin("gamma")
    alpha_wrapper.disable()
    gamma_wrapper.disable()
  return sp.hooks.score(value)