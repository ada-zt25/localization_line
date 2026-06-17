def mutate_then_read(data, key, val):
    conf = Config()
    profile_conf = ProfileConfig()
    conf.load(data)
    conf[key] = val
    return conf.get(key)