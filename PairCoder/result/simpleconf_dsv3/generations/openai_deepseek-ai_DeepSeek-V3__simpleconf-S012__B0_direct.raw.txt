def with_profile_temporary(profiles, profile):
    conf = ProfileConfig(profiles)
    with conf.with_profile(profile):
        inside = conf.x
    after = conf.x
    return (inside, after)