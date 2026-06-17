def active_profile_name(profiles, profile):
    config = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(config, profile)
    return config.current_profile()