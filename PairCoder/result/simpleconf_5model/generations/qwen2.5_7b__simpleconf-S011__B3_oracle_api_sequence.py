def switch_two_profiles(profiles):
    # Load the first ProfileConfig
    config = Config()
    
    # Switch to 'prod' profile and read x
    config.load(profiles['prod'])
    prod_x = config.read('x')
    
    # Switch back to 'default' profile and read x
    config.load(profiles['default'])
    default_x = config.read('x')
    
    return (prod_x, default_x)