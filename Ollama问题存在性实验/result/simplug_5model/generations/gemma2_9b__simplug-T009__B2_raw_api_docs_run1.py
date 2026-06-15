def disable_alpha_gamma_via_wrappers_then_score(value):
  alpha_wrapper = get_plugin('alpha')
  gamma_wrapper = get_plugin('gamma')
  alpha_wrapper.disable()
  gamma_wrapper.disable()
  return sp.hooks.score(value)