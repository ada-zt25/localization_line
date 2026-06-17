def active_profile_name(profiles, profile):
    config = ProfileConfig.load(profiles)
    with config.with_profile(config, profile):
        return config.current_profile(config)