def nested_with_profiles(profiles):
  conf = ProfileConfig.load(profiles, base='default')
  with ProfileConfig.with_profile(conf, 'prod'):
    a = conf['x']
    with ProfileConfig.with_profile(conf, 'default'):
      b = conf['x']
    c = conf['x']
  return (a, b, c)