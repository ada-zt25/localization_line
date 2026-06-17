def nested_with_profiles(profiles):
    with profiles['prod'] as conf:
        a = conf.x
        with conf.with_profile('default'):
            b = conf.x
        c = conf.x
    return (a, b, c)