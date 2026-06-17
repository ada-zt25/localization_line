def nested_with_profiles(profiles):
    conf = ProfileConfig.load(profiles, base='default')
    with conf.with_profile('prod'):
        a = conf.x
        with conf.with_profile('default'):
            b = conf.x
        c = conf.x
    return (a, b, c)