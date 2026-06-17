def use_then_with_restore(profiles):
  prof = ProfileConfig.load(profiles)
  prof.set('prod')
  with prof.with_profile('default'):
    mid = Config.x
  after = Config.x
  return mid, after