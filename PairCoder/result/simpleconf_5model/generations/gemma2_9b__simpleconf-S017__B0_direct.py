def double_use_persistent(profiles):
  conf = profiles['prod']
  conf.switch('default')
  return conf.x