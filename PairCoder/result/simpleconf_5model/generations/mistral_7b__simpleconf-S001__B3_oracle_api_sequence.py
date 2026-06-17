from simpleconf import Config, ProfileConfig

def merge_get(base, override, key):
    merged = ProfileConfig()
    base.load(merged)
    override.load(merged)
    return merged[key]