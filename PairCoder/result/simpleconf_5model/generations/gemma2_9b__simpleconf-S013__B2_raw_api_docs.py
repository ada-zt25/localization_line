def use_then_with_restore(profiles):
  prod = ProfileConfig.load(profiles['prod'])
  prod.use_profile('prod')
  with prod.with_profile('default'):
    mid = prod.x
  after = prod.x
  return (mid, after)