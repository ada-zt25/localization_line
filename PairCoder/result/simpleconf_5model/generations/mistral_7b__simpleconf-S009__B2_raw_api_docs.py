def use_profile_same_conf(profiles, profile):
    config = profiles
    original_profile = current_profile(config)
    with config.with_profile(profile):
        value = config.conf.x
    config.use_profile(original_profile)
    return value