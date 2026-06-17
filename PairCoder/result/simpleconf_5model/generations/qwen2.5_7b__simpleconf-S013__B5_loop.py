def use_then_with_restore(profiles):
    pc = ProfileConfig.load(profiles, base='default')
    prod_conf = pc.use_profile(pc, 'prod')
    mid = prod_conf.conf.x
    
    with pc.with_profile(pc, 'default'):
        after = pc.conf.x
    
    return (mid, after)