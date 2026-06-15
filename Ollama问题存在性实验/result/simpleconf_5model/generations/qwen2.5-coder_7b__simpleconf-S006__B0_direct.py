def load_then_get(data, key):
    config = Config.from_dict(data)
    return config.get(key)