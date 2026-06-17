def two_reads_same_conf(profiles):
  p = ProfileConfig.load(profiles, base='default')
  p.use_profile('prod')
  with p.with_profile('prod'):
    x1 = p.conf.x
    x2 = p.conf.x
  return (x1, x2)