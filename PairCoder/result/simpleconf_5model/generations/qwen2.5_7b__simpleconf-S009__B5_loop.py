def use_profile_same_conf(profiles, profile):
    config = ProfileConfig.load(profiles)
    original_profile = ProfileConfig.current_profile(config)
    with ProfileConfig.with_profile(config, profile):
        result = config.x
    return result