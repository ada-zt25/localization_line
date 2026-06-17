def use_then_with_restore(profiles):
    conf = Config()
    conf.load(*profiles)
    initial_profile = conf.current_profile(conf)

    with ProfileConfig.use_profile(conf, 'prod'):
        with ProfileConfig.with_profile(conf, 'default'):
            mid = conf.x

    after = conf.x
    return mid, after