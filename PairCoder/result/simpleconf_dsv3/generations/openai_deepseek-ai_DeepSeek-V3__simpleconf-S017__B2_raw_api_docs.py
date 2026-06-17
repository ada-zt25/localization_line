def double_use_persistent(profiles):
    conf = ProfileConfig.load(profiles)
    use_profile(conf, 'prod')
    use_profile(conf, 'default')
    return conf.x