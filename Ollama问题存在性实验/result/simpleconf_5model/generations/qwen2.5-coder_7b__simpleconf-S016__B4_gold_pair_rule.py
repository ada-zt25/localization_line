def use_survives_with(profiles):
    conf = ProfileConfig.load(profiles, base='default')
    ProfileConfig.use_profile(conf, 'prod')
    with ProfileConfig.with_profile(conf, 'default'):
        pass  # default here
    return conf.x