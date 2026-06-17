def active_profile_name(profiles, profile):
    config = ProfileConfig(profiles)
    config.switch_profile(profile)
    return config.active_profile