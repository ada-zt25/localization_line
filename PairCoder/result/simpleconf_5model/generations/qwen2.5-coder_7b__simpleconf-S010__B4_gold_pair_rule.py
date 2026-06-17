def mutate_then_read(data, key, val):
    conf = ProfileConfig.load(data)
    ProfileConfig.use_profile(conf, 'default')
    setattr(conf, key, val)
    return getattr(conf, key)