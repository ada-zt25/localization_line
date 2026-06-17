def load_then_get(data, key):
    conf = Config()
    conf.load(data)
    with conf.with_profile('default'):
        value = getattr(conf, key, None)
    return value