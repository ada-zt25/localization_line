def active_profile_name(profiles, profile):
  conf = ProfileConfig.load(profiles, base='default')
  with conf.with_profile(profile):
    return ProfileConfig.current_profile(conf)