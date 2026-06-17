def active_profile_name(profiles, profile):
    config = Config.load(*profiles)
    with config.use_profile(profile):
        return current_profile(config)