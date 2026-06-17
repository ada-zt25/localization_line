def use_then_with_restore(profiles):
    conf = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(conf, 'prod')
    with ProfileConfig.with_profile(conf, 'default'):
        mid = conf.x
    after = conf.x
    return (mid, after)