from simpleconf import Config, ProfileConfig

def merge_get(base, override, key):
    with base.with_profile('default'):
        base.load(base)

    with override.with_profile('default'):
        override.load(override)

    merged = ProfileConfig()
    merged.load([base, override])
    return getattr(merged, key)