def switch_two_profiles(profiles):
    profiles.switch('prod')
    prod_x = profiles.x
    profiles.switch('default')
    default_x = profiles.x
    return (prod_x, default_x)