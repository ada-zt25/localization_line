from simpleconf import Config, ProfileConfig

def load_is_diot(data):
    config = Config(data)
    return config.as_dict()