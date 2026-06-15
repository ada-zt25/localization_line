def with_profile_keeps_current(profiles):
    config = ProfileConfig()
    config.load(profiles)
    config.set_active('prod')
    
    with config.with_profile('default'):
        pass
    
    return config.get_active()