def disable_alpha_gamma_via_wrappers_then_score(value):
  alpha_wrapper = alpha.get_plugin_wrapper()
  alpha_wrapper.disable()
  gamma_wrapper = gamma.get_plugin_wrapper()
  gamma_wrapper.disable()
  return sp.hooks.score(value)