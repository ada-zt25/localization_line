def double_use_persistent(profiles):
    conf = ProfileConfig(profiles)
    conf.set_profile('prod')
    conf.set_profile('default')
    return conf.x