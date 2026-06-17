def switch_two_profiles(profiles):
    with ProfileConfig.with_profile(profiles, 'prod') as conf:
        prod_x = conf.x
    
    with ProfileConfig.with_profile(profiles, 'default') as conf:
        default_x = conf.x
    
    return (prod_x, default_x)