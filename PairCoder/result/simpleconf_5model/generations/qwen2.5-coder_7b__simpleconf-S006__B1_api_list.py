def load_then_get(data, key):
    conf = Config.load(*data)
    return getattr(conf, key)