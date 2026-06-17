def merge_get(base, override, key):
    return Config.load(base, override)[key]