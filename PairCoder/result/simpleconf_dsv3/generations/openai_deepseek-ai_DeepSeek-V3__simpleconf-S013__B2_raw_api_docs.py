def use_then_with_restore(profiles):
    conf = ProfileConfig.load(profiles)
    conf.use_profile('prod')
    
    with conf.with_profile('default'):
        mid = conf.x
    
    after = conf.x
    return (mid, after)