def merge_get(base, override, key):
    with use_profile(base, 'default'):
        base.load(override)
    return getattr(base, key)