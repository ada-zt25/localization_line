def with_profile_temporary(profiles, profile):
    conf = Config()
    conf.load(*profiles)
    original_profile = conf.current_profile(conf)

    with ProfileConfig.with_profile(conf, profile):
        inside = conf.x

    after = conf.x

    ProfileConfig.use_profile(conf, original_profile)

    return inside, after