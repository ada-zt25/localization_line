def with_profile_keeps_current(profiles):
    conf = ProfileConfig.load(profiles, base='default')
    ProfileConfig.use_profile(conf, 'prod')
    
    with ProfileConfig.with_profile(conf, 'default'):
        pass
    
    return ProfileConfig.current_profile(conf)