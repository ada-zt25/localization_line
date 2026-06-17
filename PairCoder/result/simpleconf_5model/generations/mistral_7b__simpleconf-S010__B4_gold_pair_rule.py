def mutate_then_read(data, key, val):
    conf = ProfileConfig.load(data)
    profile = ProfileConfig.current_profile(conf)
    with ProfileConfig.with_profile(conf, 'temp'):
        conf[key] = val
        result = conf[key]
    ProfileConfig.use_profile(conf, profile)
    return result