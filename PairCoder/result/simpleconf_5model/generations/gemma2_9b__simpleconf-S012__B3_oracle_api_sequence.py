def with_profile_temporary(profiles, profile):
  with profiles.load(profile) as conf:
    inside = conf.x
  after = conf.x
  return (inside, after)