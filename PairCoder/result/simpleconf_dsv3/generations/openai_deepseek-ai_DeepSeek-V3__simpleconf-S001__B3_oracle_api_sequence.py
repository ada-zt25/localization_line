def merge_get(base, override, key):
    config = Config.load([base, override])
    return config[key]