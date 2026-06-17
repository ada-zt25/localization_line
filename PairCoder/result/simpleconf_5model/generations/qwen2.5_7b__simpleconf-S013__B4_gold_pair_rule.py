def use_then_with_restore(profiles):
    conf = ProfileConfig.load(profiles, base='default')
    mid = conf.x
    ProfileConfig.use_profile(conf, 'prod')
    
    with ProfileConfig.with_profile(conf, 'default'):
        pass
    
    after = conf.x
    return mid, after