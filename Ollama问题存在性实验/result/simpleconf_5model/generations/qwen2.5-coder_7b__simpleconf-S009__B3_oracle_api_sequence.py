def use_profile_same_conf(profiles, profile):
    config = ProfileConfig()
    config.load(profiles)
    config.use_profile(profile)
    return config.conf.x