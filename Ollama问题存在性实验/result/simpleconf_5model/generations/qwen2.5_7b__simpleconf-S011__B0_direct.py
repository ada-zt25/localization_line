def switch_two_profiles(profiles):
    prod_x = profiles['prod'].get('x')
    profiles['default'].use()
    default_x = profiles['default'].get('x')
    return (prod_x, default_x)