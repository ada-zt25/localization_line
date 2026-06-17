import simpleconf

def nested_with_profiles(profiles):
    with simpleconf.Config(profiles) as config:
        with config.with_profile('prod'):
            a = config['x']
        with config.with_profile('default'):
            b = config['x']
        c = config['x']
        return (a, b, c)