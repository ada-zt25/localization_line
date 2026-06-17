def merge_three(a, b, c, key):
    merged_config = Config.load(a, b, c)
    return merged_config.get(key, None)