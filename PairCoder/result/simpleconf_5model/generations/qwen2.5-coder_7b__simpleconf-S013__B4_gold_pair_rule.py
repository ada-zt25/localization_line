def use_then_with_restore(profiles):
    conf = Config.load(ProfileConfig.load(profiles))
    ProfileConfig.use_profile(conf, 'prod')
    mid = conf.x
    with ProfileConfig.with_profile(conf, 'default'):
        pass
    after = conf.x
    return (mid, after)