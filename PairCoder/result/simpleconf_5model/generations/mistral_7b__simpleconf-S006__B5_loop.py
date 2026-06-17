def load_then_get(data, key):
    with ProfileConfig.from_dict(data).with_profile(None) as config:
        profile = ProfileConfig.current_profile(config)
        Config.load(*configs=data[profile], loader=None)
        return config[key]