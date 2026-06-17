from simpleconf import Config, ProfileConfig

def mutate_then_read(data, key, val):
    with ProfileConfig(data) as conf:
        current_profile = current_profile(conf)
        with conf.with_profile('temp'):
            conf[key] = val
            result = conf[key]
        return result