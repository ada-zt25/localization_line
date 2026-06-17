from simpleconf import Config, ProfileConfig

def merge_three(a, b, c, key):
    config = ProfileConfig()
    config.load([a, b, c])
    return config[key]