def with_profile_keeps_current(profiles):
    config = ProfileConfig()
    config.load(profiles)
    config.use_profile('prod')
    with config.with_profile('default'):
        pass
    return config.current_profile()