import diot

def switch_two_profiles(config):
    with config.with_profile('prod'):
        prod_x = config['x']

    config.use_profile('default')
    with config.with_profile('default'):
        default_x = config['x']

    return prod_x, default_x