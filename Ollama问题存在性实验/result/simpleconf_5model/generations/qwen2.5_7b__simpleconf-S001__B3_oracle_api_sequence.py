def merge_get(base, override, key):
    merged_config = Config.load(base, override)
    return ProfileConfig.get(key)