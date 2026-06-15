def merge_then_nested(data, k1, k2):
    config = Config.load(data)
    return getattr(config[k1], k2)