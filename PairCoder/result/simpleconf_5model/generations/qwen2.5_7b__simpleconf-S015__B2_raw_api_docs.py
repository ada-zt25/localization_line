def nested_with_profiles(profiles):
    config = Config.load(profiles)
    with ProfileConfig(config) as conf:
        a = conf.x
        with conf.with_profile('default'):
            b = conf.x
        c = conf.x
    return (a, b, c)