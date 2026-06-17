def profile_value(profiles, profile):
    config = ProfileConfig.load(profiles, base='default')
    with config.with_profile(config, profile):
        return config.x