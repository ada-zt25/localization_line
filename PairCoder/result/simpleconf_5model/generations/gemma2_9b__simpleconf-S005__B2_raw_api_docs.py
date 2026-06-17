def active_profile_name(profiles, profile):
  Config.load(profiles)
  ProfileConfig.use_profile(Config, profile)
  return ProfileConfig.current_profile(Config)