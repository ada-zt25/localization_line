from simpleconf import Config, ProfileConfig

def double_use_persistent(profiles):
    with ProfileConfig.load(profiles, base='default') as conf:
        with conf.with_profile('prod'):
            conf.save()

        with conf.with_profile('default'):
            return conf.x