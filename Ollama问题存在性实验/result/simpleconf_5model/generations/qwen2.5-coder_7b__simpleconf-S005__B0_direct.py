def active_profile_name(profiles, profile):
    config = ProfileConfig()
    config.load(profiles)
    config.switch_to(profile)
    return config.active_profile_name()