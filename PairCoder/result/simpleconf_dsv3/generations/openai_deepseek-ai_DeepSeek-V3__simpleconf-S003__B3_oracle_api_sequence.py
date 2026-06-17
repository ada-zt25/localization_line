def load_is_diot(data):
    config = Config.load(data)
    return ProfileConfig(config)