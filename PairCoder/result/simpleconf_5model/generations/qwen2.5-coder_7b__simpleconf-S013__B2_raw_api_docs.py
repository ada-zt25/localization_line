def use_then_with_restore(profiles):
    conf = Config()
    ProfileConfig(conf, profiles)
    use_profile(conf, 'prod')
    mid = conf.x
    with with_profile(conf, 'default'):
        after = conf.x
    return (mid, after)