def switch_two_profiles(profiles):
    conf = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(conf, 'prod')
    prod_x = conf.x
    ProfileConfig.use_profile(conf, 'default')
    default_x = conf.x
    return (prod_x, default_x)