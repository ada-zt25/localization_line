from simpleconf import ProfileConfig

def with_profile_temporary(profiles, profile):
    inside = None
    after = None
    
    with profiles.with_profile(profile) as conf:
        inside = conf.x
    
    after = profiles.default_profile().x
    
    return (inside, after)