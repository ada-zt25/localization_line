from simpleconf import Config, ProfileConfig

def load_then_get(data, key):
    conf = Config()
    conf.load(data)
    return conf[key]