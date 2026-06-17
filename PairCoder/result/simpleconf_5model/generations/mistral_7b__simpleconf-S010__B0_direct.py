from simpleconf import Config, ProfileConfig

def mutate_then_read(data, key, val):
    config = ProfileConfig(data)
    config[key] = val
    return config[key]