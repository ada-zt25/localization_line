def profile_load_attr(profiles):
  profile = ProfileConfig.load(profiles)
  return profile.conf.x