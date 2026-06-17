from simpleconf import Config, ProfileConfig

def load_is_diot(data):
    config = Config.load(data)
    return ProfileConfig(config)