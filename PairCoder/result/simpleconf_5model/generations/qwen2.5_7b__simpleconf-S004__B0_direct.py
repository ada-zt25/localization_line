def profile_value(profiles, profile):
    conf = ProfileConfig()
    profiles.load_profile(conf, profile)
    return conf.x