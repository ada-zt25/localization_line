def use_profile_same_conf(profiles, profile):
    config = ProfileConfig.load(profiles, base='default')
    with config.with_profile(profile) as conf:
        return conf['conf.x']