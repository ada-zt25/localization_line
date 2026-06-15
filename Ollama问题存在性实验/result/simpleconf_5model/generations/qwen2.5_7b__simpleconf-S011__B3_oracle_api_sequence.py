def switch_two_profiles(profiles):
    prod_x = profiles.use_profile('prod').x
    default_x = profiles.use_profile('default').x
    return (prod_x, default_x)