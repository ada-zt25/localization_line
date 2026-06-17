def double_use_persistent(profiles):
  conf = Config()
  conf.load(profiles)
  with ProfileConfig.with_profile(conf, 'prod'):
    pass
  conf.use_profile('default')
  return conf.x