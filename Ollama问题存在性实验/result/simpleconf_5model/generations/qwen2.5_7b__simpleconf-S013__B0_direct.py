from simpleconf import ProfileConfig

def use_then_with_restore(profiles):
    with ProfileConfig('prod', profiles) as conf:
        mid = conf.x
        with conf.with_profile('default'):
            pass
        after = conf.x
    return mid, after