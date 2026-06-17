def with_profile_keeps_current(profiles):
  with ProfileConfig(profiles).load('prod'):
    with simpleconf.with_profile('default'):
      pass
  return Config.active_profile