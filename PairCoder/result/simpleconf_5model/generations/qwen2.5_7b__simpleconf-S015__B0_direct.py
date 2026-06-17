from simpleconf import Config, ProfileConfig

def nested_with_profiles(profiles):
    config = Config()
    with config.ProfileConfig('prod') as prod_config:
        a = prod_config.read('x')
        with prod_config.with_profile('default'):
            b = prod_config.read('x')
        c = prod_config.read('x')
    return (a, b, c)