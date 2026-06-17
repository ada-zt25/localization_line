def load_then_get(data, key):
    Config.load(*data)
    return Config[key]