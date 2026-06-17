def profile_value(profiles, profile):
    conf = ProfileConfig.load(profiles)
    conf.switch_profile(profile)
    return conf.x