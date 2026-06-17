def switch_two_profiles(profiles):
    prod_config = ProfileConfig.load(profiles)
    with ProfileConfig.with_profile(prod_config, 'prod'):
        prod_x = prod_config.x
    default_config = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(default_config, 'default')
    default_x = default_config.x
    return prod_x, default_x