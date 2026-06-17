def double_use_persistent(profiles):
  conf = ProfileConfig.load(profiles, base='default')
  ProfileConfig.use_profile(conf, 'prod')
  ProfileConfig.use_profile(conf, 'default')
  return conf.x