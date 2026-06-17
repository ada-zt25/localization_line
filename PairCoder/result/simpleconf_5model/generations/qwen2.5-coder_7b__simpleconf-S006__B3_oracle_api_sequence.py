def load_then_get(data, key):
    config = Config.load(data)
    return config.read(key)