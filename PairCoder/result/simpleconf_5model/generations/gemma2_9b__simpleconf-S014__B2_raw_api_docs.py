def with_profile_keeps_current(profiles):
  prod_config = ProfileConfig.load(profiles)
  prod_config.use_profile('prod')
  with prod_config.with_profile('default'):
    pass
  return prod_config.current_profile()