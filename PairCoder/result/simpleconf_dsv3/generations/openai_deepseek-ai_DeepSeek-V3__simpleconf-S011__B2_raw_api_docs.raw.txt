def switch_two_profiles(profiles):
    with with_profile(profiles, 'prod'):
        prod_x = profiles.x
    with with_profile(profiles, 'default'):
        default_x = profiles.x
    return (prod_x, default_x)