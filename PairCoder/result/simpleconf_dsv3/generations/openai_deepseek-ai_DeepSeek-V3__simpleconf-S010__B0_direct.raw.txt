def mutate_then_read(data, key, val):
    conf = Config.loads(data)
    conf[key] = val
    return conf[key]