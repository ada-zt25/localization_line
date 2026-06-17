def use_survives_with(profiles):
    with ProfileConfig.load(profiles, base='default').with_profile('default'):
        original_profile = ProfileConfig.current_profile(None)
        ProfileConfig.use_profile(None, 'prod')
        conf = Config.load(*[ProfileConfig.load(['prod'])])
        result = conf.x
    ProfileConfig.use_profile(None, original_profile)
    return result