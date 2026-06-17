def with_profile_keeps_current(profiles):
    config = Config()
    prod_config = ProfileConfig('prod')
    config.load(prod_config)
    
    with profiles.with_profile('default'):
        pass
    
    return config.active_profile.name