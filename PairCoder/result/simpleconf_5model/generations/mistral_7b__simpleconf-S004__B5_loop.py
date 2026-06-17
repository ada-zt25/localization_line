def profile_value(profiles, profile):
    with ProfileConfig.load(profiles, base='default').with_profile(profile):
        return conf.x