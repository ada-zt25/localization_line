def merge_then_nested(data, k1, k2):
    return Config.load(data)[k1][k2]