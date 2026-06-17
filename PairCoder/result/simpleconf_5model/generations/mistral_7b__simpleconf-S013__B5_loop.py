import simpleconf

def use_then_with_restore(profiles):
    with profiles.ProfileConfig.load(profiles, base='default').thaw() as conf:
        conf.use_profile('prod')
        mid = conf.x

    with profiles.ProfileConfig.with_profile(conf, 'default').thaw() as conf:
        after = conf.x

    return (mid, after)