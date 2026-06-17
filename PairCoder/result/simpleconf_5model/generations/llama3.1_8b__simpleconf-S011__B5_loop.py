def switch_two_profiles(profiles):
    prod_config = profiles['prod']
    default_config = profiles['default']

    with ProfileConfig.use_profile(prod_config, 'prod'):
        prod_x = prod_config.x

    with ProfileConfig.use_profile(default_config, 'default'):
        default_x = default_config.x

    return prod_x, default_x