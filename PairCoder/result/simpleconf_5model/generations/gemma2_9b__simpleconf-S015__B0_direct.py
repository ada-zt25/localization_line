def nested_with_profiles(profiles):
  with profiles.ProfileConfig('prod') as config:
    a = config.x
    with config.with_profile('default'):
      b = config.x
    c = config.x
  return (a, b, c)