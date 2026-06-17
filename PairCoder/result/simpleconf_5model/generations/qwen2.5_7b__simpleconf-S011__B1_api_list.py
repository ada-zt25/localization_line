def switch_two_profiles(profiles):
    prod_x = None
    default_x = None
    
    with ProfileConfig.with_profile(ProfileConfig.load(profiles), 'prod') as conf:
        prod_x = conf.x
    
    with ProfileConfig.with_profile(ProfileConfig.load(profiles), 'default') as conf:
        default_x = conf.x
    
    return (prod_x, default_x)