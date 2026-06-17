def merge_three(a, b, c, key):
    config = Config.load([a, b, c])
    return config[key]