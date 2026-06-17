def switch_two_profiles(profiles):
    config = ProfileConfig.load(profiles)
    config.switch_profile('prod')
    prod_x = config.x
    config.switch_profile('default')
    default_x = config.x
    return (prod_x, default_x)