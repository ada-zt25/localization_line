def use_survives_with(profiles):
    prod = ProfileConfig.load(profiles, base='default')
    ProfileConfig.use_profile(prod.config, 'prod')

    with ProfileConfig.with_profile(prod.config, 'default'):
        pass

    return prod.config['x']