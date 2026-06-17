from simpleconf import Config, ProfileConfig

def use_survives_with(profiles):
    with ProfileConfig.load(profiles, base='default').with_profile('default'):
        Config.load(['prod'])
        ProfileConfig.use_profile(None, 'prod')
        return Conf.x