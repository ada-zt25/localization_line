def with_profile_temporary(profiles, profile):
  Config.load(profiles)
  with with_profile(Config, profile):
    inside = conf.x
  after = conf.x
  return (inside, after)