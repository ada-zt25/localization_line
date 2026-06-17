def use_then_with_restore(profiles):
    conf = ProfileConfig.load(profiles, base='default')
    ProfileConfig.use_profile(conf, 'prod')
    mid = conf.x
    with ProfileConfig.with_profile(conf, 'default'):
        pass
    after = conf.x
    return (mid, after)