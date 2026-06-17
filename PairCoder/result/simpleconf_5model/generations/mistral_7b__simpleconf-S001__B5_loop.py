import simpleconf

def merge_get(base, override, key):
    with base.with_profile(''):  # switch to an empty profile temporarily
        base.load(*[base])  # reload base config to clear any active profile

    with base.with_profile('override'):  # switch to the override profile temporarily
        override_config = ProfileConfig.load(override, base='default')
        base.load(override_config)  # merge override into base

    result = base[key]  # get the value for key from the merged config
    return result