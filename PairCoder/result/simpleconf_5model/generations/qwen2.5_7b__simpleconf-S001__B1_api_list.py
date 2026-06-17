def merge_get(base, override, key):
    merged_config = base.load(override)
    return merged_config[key]