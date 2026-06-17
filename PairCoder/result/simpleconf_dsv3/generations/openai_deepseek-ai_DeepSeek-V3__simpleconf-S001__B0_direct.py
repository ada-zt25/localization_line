def merge_get(base, override, key):
    config = Config.load(base)
    override_config = ProfileConfig.load(override)
    merged = config.merge(override_config)
    return merged[key]