def load_is_diot(data):
    config = Config()
    config.load([data])
    profile_config = ProfileConfig()
    with profile_config.with_profile(config, 'default'):
        return profile_config