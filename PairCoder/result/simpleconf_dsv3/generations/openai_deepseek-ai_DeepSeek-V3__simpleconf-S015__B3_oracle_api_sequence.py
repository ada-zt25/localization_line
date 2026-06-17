def nested_with_profiles(profiles):
    config = ProfileConfig.load(profiles)
    with config.with_profile('prod'):
        a = config.x
        with config.with_profile('default'):
            b = config.x
        c = config.x
    return (a, b, c)