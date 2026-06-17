def use_then_with_restore(profiles):
  with profiles.load('prod') as mid:
    with profiles.with_profile('default'):
      x = Config.x
    after = Config.x
  return (mid, after)