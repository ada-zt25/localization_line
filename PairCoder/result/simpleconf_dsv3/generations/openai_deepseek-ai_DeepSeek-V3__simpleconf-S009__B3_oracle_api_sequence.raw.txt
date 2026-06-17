def use_profile_same_conf(profiles, profile):
    conf = ProfileConfig.load(profiles)
    conf.switch_profile(profile)
    return conf.x