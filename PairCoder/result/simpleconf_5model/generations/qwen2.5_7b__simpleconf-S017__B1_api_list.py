from simpleconf import Config, ProfileConfig

def double_use_persistent(profiles):
    conf = ProfileConfig.load(profiles, base='default')
    with ProfileConfig.with_profile(conf, 'prod'):
        pass
    ProfileConfig.use_profile(conf, 'default')
    return conf.x