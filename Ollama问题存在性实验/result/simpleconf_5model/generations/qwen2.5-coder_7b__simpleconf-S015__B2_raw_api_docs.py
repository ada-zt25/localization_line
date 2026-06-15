def nested_with_profiles(profiles):
    config = Config.load(profiles)
    with with_profile(config, 'prod') as prod_conf:
        a = prod_conf.x
        with with_profile(prod_conf, 'default') as default_conf:
            b = default_conf.x
        c = prod_conf.x
    return (a, b, c)