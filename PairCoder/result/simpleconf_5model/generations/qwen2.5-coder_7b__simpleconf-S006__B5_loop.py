def load_then_get(data, key):
    config = Config.load(ProfileConfig.load(data))
    return getattr(config, key)