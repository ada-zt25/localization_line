from simpleconf import Config, ProfileConfig

def mutate_then_read(data, key, val):
    conf = Config.load(data)
    base_profile = current_profile(conf)
    use_profile(conf, 'default')
    conf[key] = val
    use_profile(conf, base_profile)
    return conf[key]