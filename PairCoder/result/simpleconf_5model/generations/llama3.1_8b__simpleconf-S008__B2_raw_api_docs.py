def merge_then_nested(data, k1, k2):
    conf = Config.load(data)
    return getattr(conf[k1], k2)