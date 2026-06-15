def mutate_then_read(data, key, val):
    conf = Config.load()
    conf[ProfileConfig(key)] = val
    return conf[ProfileConfig(key)]