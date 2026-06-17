def use_survives_with(profiles):
  p = profiles['prod']
  with p.load():
    with with_profile('default'):
      pass
  return conf.x