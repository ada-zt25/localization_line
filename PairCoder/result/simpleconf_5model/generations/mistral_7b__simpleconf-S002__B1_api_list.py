from simpleconf import Config, ProfileConfig

def merge_three(a, b, c, key):
    with ProfileConfig('merged', base=a).with_profile('first'):
        ProfileConfig.load([b])
        with ProfileConfig('merged', base=ProfileConfig.current_profile()).with_profile('second'):
            ProfileConfig.load([c])
            merged = Config.load((ProfileConfig,))
    return merged[key]