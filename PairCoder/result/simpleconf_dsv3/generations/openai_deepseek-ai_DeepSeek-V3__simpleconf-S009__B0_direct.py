def use_profile_same_conf(profiles, profile):
    config = ProfileConfig(profiles)
    config.switch_profile(profile)
    return config.conf.x