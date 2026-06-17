def load_then_get(data, key):
    conf = Config()
    conf.load(data)
    return getattr(conf, key, None)