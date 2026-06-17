def switch_two_profiles(profiles):
    from simpleconf import ProfileConfig, use_profile

    with ProfileConfig.load(profiles) as conf:
        prod_x = use_profile(conf, 'prod').x
        with use_profile(conf, 'default'):
            default_x = conf.x
    return (prod_x, default_x)