def mutate_then_read(data, key, val):
    conf = Config.load(*data)
    setattr(conf, key, val)
    return getattr(conf, key)