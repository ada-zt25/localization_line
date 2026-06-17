def profile_value(profiles, profile):
    conf = ProfileConfig.load(profiles, base='default')
    with ProfileConfig.with_profile(conf, profile):
        return conf['x']