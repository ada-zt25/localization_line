def with_profile_temporary(profiles, profile):
    conf = Config.load(ProfileConfig.load(profiles))
    inside = conf.x
    with ProfileConfig.with_profile(conf, profile):
        after = conf.x
    return (inside, after)