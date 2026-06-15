def merge_three(a, b, c, key):
    merged_config = Config.load(a, b, c)
    return getattr(merged_config, key, None)