def profile_value(profiles, profile):
    config = Config()
    profiles.load(config)
    config.switch_to(profile)
    return config.x