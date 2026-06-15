def use_then_with_restore(profiles):
    conf = ProfileConfig.load(profiles, base='default')
    prod_profile = 'prod'
    ProfileConfig.use_profile(conf, prod_profile)
    
    mid = conf.x
    
    with ProfileConfig.with_profile(conf, 'default'):
        after = conf.x
    
    return mid, after