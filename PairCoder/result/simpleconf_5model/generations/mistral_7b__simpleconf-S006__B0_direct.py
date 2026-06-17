from simpleconf import Config, ProfileConfig

def load_then_get(data, key):
    config = ProfileConfig(data)
    return config[key]