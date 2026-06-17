def use_survives_with(profiles):
    prod = ProfileConfig.load(profiles, base='default')
    ProfileConfig.use_profile(prod, 'prod')

    with ProfileConfig.with_profile(prod, 'default'):
        pass

    return prod['x']