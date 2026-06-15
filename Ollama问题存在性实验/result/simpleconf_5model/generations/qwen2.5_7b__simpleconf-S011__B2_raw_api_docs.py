def switch_two_profiles(profiles):
    from simpleconf import ProfileConfig, current_profile

    conf = profiles.load()
    prod_x = None
    default_x = None

    with ProfileConfig.with_profile(conf, 'prod'):
        prod_x = conf.x

    with ProfileConfig.use_profile(conf):
        default_x = conf.x

    return (prod_x, default_x)