def load_then_get(data, key):
    config = Config()
    profile_config = ProfileConfig(config)
    return profile_config.get(key)