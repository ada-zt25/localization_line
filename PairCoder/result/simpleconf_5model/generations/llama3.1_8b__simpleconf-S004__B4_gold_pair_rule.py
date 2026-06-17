def profile_value(profiles, profile):
    with profiles.load(base='default').with_profile(profile) as conf:
        return conf.x