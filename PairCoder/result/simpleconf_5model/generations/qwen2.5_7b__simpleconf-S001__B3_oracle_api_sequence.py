def merge_get(base, override, key):
    merged_config = base.load()
    merged_config.update(override.load())
    return merged_config.get(key)