from simpleconf import Config, ProfileConfig

def merge_three(a, b, c, key):
    with ProfileConfig('merged') as merged:
        merged.use_profile('base').load(a)
        merged.use_profile('intermediate').load(b)
        merged.use_profile('final').load(c)

    return getattr(merged, key)