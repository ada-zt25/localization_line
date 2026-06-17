def active_profile_name(profiles, profile):
    config = ProfileConfig.load(profiles, base='default')
    with config.with_profile(profile):
        return config.current_profile(config)