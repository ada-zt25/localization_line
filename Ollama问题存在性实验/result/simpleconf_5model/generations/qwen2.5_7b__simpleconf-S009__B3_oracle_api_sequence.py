def use_profile_same_conf(profiles, profile):
    config = ProfileConfig.load()
    profiles.use_profile(config, profile)
    return config.conf.x