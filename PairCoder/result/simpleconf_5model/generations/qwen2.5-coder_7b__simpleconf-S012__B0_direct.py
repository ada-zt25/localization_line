def with_profile_temporary(profiles, profile):
    inside = None
    after = None
    
    with ProfileConfig(profiles, profile) as conf:
        inside = conf.x
        
    after = Config().x
    
    return (inside, after)