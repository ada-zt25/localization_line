def with_profile_temporary(profiles, profile):
    conf = ProfileConfig.load(profiles)
    initial_value = conf.x
    with ProfileConfig.with_profile(conf, profile):
        inside_value = conf.x
    after_value = conf.x
    return (inside_value, after_value)