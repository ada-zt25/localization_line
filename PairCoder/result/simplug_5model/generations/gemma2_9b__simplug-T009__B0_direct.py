def disable_alpha_gamma_via_wrappers_then_score(value):
  sp, alpha, beta, gamma = make_score_manager()
  alpha_wrapper = alpha.get_wrapper()
  alpha_wrapper.disable()
  gamma_wrapper = gamma.get_wrapper()
  gamma_wrapper.disable()
  return sp.hooks.score(value)