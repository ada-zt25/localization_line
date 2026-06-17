def with_profile_temporary(profiles, profile):
  with with_profile(profile):
    inside = Config().x
  after = Config().x
  return (inside, after)