def double_use_persistent(profiles):
    conf = Config.load(profiles)
    ProfileConfig.use_profile(conf, 'prod')
    ProfileConfig.use_profile(conf, 'default')
    return conf.x