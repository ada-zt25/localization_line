def nested_with_profiles(profiles):
    with ProfileConfig(profiles['prod']) as config:
        a = config.read('x')
        with ProfileConfig(profiles['default']) as config:
            b = config.read('x')
        c = config.read('x')
    return (a, b, c)