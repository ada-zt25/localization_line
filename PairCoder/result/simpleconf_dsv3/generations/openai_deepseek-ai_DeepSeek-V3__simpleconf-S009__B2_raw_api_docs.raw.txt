def use_profile_same_conf(profiles, profile):
    conf = ProfileConfig.load(profiles)
    conf.use_profile(profile)
    return conf.x