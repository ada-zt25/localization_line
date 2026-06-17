def nested_with_profiles(profiles):
  merged = ProfileConfig.load(profiles, base='default')
  with ProfileConfig.with_profile(merged, 'prod'):
    a = merged['x']
    with ProfileConfig.with_profile(merged, 'default'):
      b = merged['x']
    c = merged['x']
  return (a, b, c)