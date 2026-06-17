def with_profile_keeps_current(profiles):
    conf = ProfileConfig.load(profiles)
    conf.use_profile('prod')
    with conf.with_profile('default'):
        pass
    return conf.current_profile()