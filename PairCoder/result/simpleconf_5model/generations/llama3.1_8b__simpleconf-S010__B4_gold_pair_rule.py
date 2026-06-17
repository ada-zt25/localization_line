def mutate_then_read(data, key, val):
    config = ProfileConfig.load(profiles)
    config.use_profile(config, 'prod')
    config[key] = val
    return config[key]