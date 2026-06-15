def merge_get(base, override, key):
    merged_config = base.load(override, loader=None)
    return merged_config[key]