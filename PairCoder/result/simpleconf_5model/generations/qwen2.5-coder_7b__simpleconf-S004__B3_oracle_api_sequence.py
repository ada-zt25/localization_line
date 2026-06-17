def profile_value(profiles, profile):
    config = ProfileConfig.load(profiles)
    config.select_profile(profile)
    return config.conf.x