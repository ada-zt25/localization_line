def active_profile_name(profiles, profile):
    conf = Config()
    conf.load(*profiles)
    with conf.with_profile(profile):
        return current_profile(conf)