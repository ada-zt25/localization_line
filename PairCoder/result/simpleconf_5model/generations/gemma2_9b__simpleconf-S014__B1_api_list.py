def with_profile_keeps_current(profiles):
  prod_config = ProfileConfig.load(profiles, base='default')
  prod_config.use_profile(prod_config, 'prod')
  with prod_config.with_profile(prod_config, 'default'):
    pass
  return prod_config.current_profile(prod_config)