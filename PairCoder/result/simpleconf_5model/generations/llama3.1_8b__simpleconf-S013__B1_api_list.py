def use_then_with_restore(profiles):
    prod = ProfileConfig.load(profiles, base='default')
    prod.use_profile(prod, 'prod')

    with prod.with_profile(prod, 'default'):
        mid = prod.conf.x

    after = prod.current_profile(prod)
    return (mid, after)