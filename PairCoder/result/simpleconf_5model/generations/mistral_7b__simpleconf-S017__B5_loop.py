import simpleconf

def double_use_persistent(profiles):
    with ProfileConfig.load(profiles, base='default') as conf:
        with conf.with_profile('prod'):
            conf.x = conf.x * 2
        profile = conf.current_profile(conf)
        with conf.use_profile('default'):
            pass
        return conf.x