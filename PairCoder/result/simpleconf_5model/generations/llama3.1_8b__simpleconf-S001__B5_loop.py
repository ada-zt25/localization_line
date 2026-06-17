def merge_get(base, override, key):
    merged = Config.load(override, loader=base)
    return merged.get(key)