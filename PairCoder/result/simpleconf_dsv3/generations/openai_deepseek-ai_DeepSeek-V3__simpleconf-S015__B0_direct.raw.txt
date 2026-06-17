def nested_with_profiles(profiles):
    with ProfileConfig(profiles, 'prod') as prod:
        a = prod.x
        with ProfileConfig(profiles, 'default') as default:
            b = default.x
        c = prod.x
    return (a, b, c)