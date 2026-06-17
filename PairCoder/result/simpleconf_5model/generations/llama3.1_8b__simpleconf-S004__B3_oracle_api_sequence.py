def profile_value(profiles, profile):
    config = Config()
    ProfileConfig.load(config, profiles)
    config.select_profile(profile)
    return config.conf.x