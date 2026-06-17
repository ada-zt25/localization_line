def with_profile_temporary(profiles, profile):
    inside = None
    after = None
    
    config = ProfileConfig(profiles)
    
    with config.with_profile(profile) as conf:
        inside = conf.x
    
    after = config.conf.x
    
    return (inside, after)