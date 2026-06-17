def load_then_get(data, key):
    with ProfileConfig.with_profile(None, Config.load(data)) as config:
        return config[key]