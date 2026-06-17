def profile_value(profiles, profile):
  conf = Config.load(profiles)
  conf.use_profile(profile)
  return conf.x