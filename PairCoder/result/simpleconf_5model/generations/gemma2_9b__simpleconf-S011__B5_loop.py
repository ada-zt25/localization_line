def switch_two_profiles(profiles):
  conf = Config.load(*profiles, loader=None)
  with ProfileConfig.with_profile(conf, 'prod'):
    prod_x = conf['x']
  with ProfileConfig.with_profile(conf, 'default'):
    default_x = conf['x']
  return (prod_x, default_x)