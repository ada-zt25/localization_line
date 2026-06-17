def profile_value(profiles, profile):
    conf = Config.load(profiles)
    with ProfileConfig(conf).use_profile(profile):
        return getattr(conf, 'x')