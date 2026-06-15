def double_use_persistent(profiles):
    conf = profiles.load()
    profiles.use_profile('prod', conf)
    profiles.use_profile('default', conf)
    return conf.x