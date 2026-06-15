def merge_three(a, b, c, key):
    merged_config = ProfileConfig()
    merged_config.update(Config(a))
    merged_config.update(Config(b))
    merged_config.update(Config(c))
    return merged_config.get(key)