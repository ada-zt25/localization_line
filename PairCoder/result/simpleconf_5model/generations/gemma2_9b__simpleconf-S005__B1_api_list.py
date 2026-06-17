def active_profile_name(profiles, profile):
  with ProfileConfig.with_profile(Config.load(profiles), profile):
    return ProfileConfig.current_profile(Config)