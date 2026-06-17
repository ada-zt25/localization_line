def mutate_then_read(data, key, val):
    config = Config.load(data)
    config[key] = val
    return config[key]