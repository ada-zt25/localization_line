def load_then_get(data, key):
    config = Config()
    profile_config = ProfileConfig(config)
    profile_config.load_from_data(data)
    return profile_config.get(key)