def load_then_get(data, key):
    with ProfileConfig.with_profile('default') as config:
        config.load(*data)
        return config[key]