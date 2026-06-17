def use_survives_with(profiles):
    conf = Config.load(profiles)
    ProfileConfig.use_profile(conf, 'prod')
    
    with ProfileConfig.with_profile(conf, 'default'):
        pass
    
    return conf.x