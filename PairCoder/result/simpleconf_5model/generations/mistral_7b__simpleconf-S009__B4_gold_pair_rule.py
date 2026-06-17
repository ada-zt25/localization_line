def use_profile_same_conf(profiles, profile):
    conf = ProfileConfig.load(profiles, base='default')
    with conf.with_profile(profile):
        return conf.x