from simpleconf import Config, ProfileConfig

def merge_three(a, b, c, key):
    with ProfileConfig.with_profile('merged', base='default'):
        merged = Config.load([ProfileConfig(a), ProfileConfig(b), ProfileConfig(c)])
    return merged[key]