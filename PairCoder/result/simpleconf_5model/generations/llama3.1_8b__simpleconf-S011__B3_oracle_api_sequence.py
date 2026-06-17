def switch_two_profiles(profiles):
    config = Config()
    config.load(profiles['prod'])
    
    prod_x = config.get('x')
    
    config.switch_profile(profiles['default'])
    
    default_x = config.get('x')
    
    return (prod_x, default_x)