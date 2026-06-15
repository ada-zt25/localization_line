def get_beta_wrapper_disable_then_score(value):
  beta_wrapper = sp.get_plugin_wrapper('beta')
  beta_wrapper.enabled = False
  return sp.hooks.score(value)