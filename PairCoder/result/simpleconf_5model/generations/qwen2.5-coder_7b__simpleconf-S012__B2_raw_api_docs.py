def with_profile_temporary(profiles, profile):
    conf = Config()
    ProfileConfig(conf, profiles)
    inside = conf.x
    with use_profile(conf, profile):
        after = conf.x
    return (inside, after)