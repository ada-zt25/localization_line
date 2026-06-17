def switch_two_profiles(profiles):
    with ProfileConfig(profiles, 'default') as conf:
        prod_x = conf.prod.x
        with use_profile(conf, 'prod'):
            default_x = conf.default.x
    return (prod_x, default_x)