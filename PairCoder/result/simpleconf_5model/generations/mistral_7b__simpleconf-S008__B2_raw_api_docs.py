from simpleconf import Config, ProfileConfig

def merge_then_nested(data, k1, k2):
    config = Config()
    for source in data:
        config.load(source)

    with ProfileConfig(config).with_profile('default'):
        return getattr(config[k1], k2)