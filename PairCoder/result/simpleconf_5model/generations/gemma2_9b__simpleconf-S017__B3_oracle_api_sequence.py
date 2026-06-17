def double_use_persistent(profiles):
  conf = Config()
  profile = profiles['prod']
  conf.load(profile)
  conf.set_profile('default')
  return conf.x