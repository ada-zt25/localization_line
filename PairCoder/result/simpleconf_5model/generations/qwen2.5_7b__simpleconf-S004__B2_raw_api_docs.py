def profile_value(profiles, profile):
    conf = ProfileConfig.load(profiles)
    use_profile(conf, profile)
    return conf.x