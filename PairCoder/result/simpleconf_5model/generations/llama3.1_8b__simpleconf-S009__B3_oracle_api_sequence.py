def use_profile_same_conf(profiles, profile):
    config = Config()
    ProfileConfig.load(config, profiles)
    config.switch_active_profile(profile)
    return config.conf.x