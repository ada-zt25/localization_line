def active_profile_name(profiles, profile):
    config = ProfileConfig.load(profiles)
    config.select_profile(profile)
    return config.active_profile_name