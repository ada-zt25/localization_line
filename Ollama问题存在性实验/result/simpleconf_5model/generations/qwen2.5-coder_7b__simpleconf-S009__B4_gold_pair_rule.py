def use_profile_same_conf(profiles, profile):
    conf = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(conf, profile)
    return conf.x