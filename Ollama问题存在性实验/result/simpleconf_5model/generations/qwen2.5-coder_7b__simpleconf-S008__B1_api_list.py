def merge_then_nested(data, k1, k2):
    config = Config.load(ProfileConfig.load(data))
    return config[k1][k2]