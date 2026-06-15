def mutate_then_read(data, key, val):
    conf = Config.load(ProfileConfig.load(['default']))
    conf[key] = val
    return conf[key]