def with_profile_temporary(profiles, profile):
    from simpleconf import ProfileConfig
    
    inside = None
    after = None
    
    config = Config()
    
    # Load default configuration
    profiles.load()
    
    # Read conf.x inside the specified profile scope
    with profiles.with_profile(profile):
        inside = profiles.read('x')
    
    # Revert to default profile and read conf.x again
    after = profiles.read('x')
    
    return (inside, after)