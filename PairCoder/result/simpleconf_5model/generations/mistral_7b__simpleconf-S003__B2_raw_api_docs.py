from simpleconf import Config, ProfileConfig

def load_is_diot(data):
    config = Config()
    config.load(data)
    profile_config = ProfileConfig(config)
    with profile_config.with_profile('default'):
        config.load({'default': data})
    return config