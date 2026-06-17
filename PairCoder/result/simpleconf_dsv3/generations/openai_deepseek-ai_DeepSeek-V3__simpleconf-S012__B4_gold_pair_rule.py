def with_profile_temporary(profiles, profile):
    conf = ProfileConfig.load(profiles)
    with ProfileConfig.with_profile(conf, profile):
        inside = conf.x
    after = conf.x
    return (inside, after)