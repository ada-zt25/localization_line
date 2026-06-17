from simpleconf import Config, ProfileConfig

def switch_two_profiles(profiles):
    conf = ProfileConfig.load(profiles, base='default')
    with conf.with_profile('prod'):
        prod_x = conf.x
    conf.use_profile('default')
    with conf.with_profile('default'):
        default_x = conf.x
    return prod_x, default_x