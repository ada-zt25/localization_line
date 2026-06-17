def switch_two_profiles(profiles):
  with with_profile(Config.load(profiles), 'prod'):
    prod_x = x 
  with with_profile(Config.load(profiles), 'default'):
    default_x = x
  return (prod_x, default_x)