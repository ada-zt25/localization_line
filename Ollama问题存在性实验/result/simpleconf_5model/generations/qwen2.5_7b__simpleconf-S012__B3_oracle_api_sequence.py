from simpleconf import ProfileConfig, with_profile

def with_profile_temporary(profiles, profile):
    config = ProfileConfig(profiles)
    inside = config.x
    with with_profile(config, profile):
        after = config.x
    return inside, after