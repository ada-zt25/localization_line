def profile_value(profiles, profile):
  conf = ProfileConfig.load(profiles, base='default')
  ProfileConfig.use_profile(conf, profile)
  return conf.x