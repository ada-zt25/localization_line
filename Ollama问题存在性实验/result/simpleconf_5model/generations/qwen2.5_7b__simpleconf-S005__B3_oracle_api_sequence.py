def active_profile_name(profiles, profile):
    config = Config()
    config.load(profiles)
    config.use_profile(profile)
    return config.current_profile()