def with_profile_temporary(profiles, profile):
    config = Config.load(*profiles)
    pc = ProfileConfig(config)
    
    inside = None
    after = None
    
    with pc.with_profile(profile):
        inside = pc.current_profile()
        assert inside == profile, "Profile should be temporarily set to the specified one"
        inside = config.conf.x
    
    after = config.conf.x
    return (inside, after)