def with_profile_temporary(profiles, profile):
    conf = ProfileConfig(profiles)
    inside = conf.x
    with conf.with_profile(profile):
        pass
    after = conf.x
    return (inside, after)