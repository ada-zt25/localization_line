import simpleconf

def nested_with_profiles(profiles):
    with ProfileConfig.load(profiles, base='default').use_profile('prod'):
        with ProfileConfig.load({'default'}).with_profile('default'):
            a = config['x']
            b = config['x']
        c = config['x']
    return (a, b, c)