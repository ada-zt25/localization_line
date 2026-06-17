from simpleconf import Config, ProfileConfig

def merge_get(base, override, key):
    with ProfileConfig.with_profile(base, base.current_profile()):
        base.load([ProfileConfig(base), override])
    return getattr(base, key)