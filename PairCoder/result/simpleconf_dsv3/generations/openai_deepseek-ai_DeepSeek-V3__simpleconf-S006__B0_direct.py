def load_then_get(data, key):
    config = Config.loads(data)
    return config[key]