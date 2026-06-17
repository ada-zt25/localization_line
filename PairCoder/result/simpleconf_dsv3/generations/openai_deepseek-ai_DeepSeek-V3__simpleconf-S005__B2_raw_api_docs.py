def active_profile_name(profiles, profile):
    conf = ProfileConfig.load(profiles)
    conf.use_profile(profile)
    return conf.current_profile()