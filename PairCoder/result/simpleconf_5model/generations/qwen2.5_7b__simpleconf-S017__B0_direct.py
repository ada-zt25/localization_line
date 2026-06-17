def double_use_persistent(profiles):
    conf = Config()
    profiles.load(conf)
    profiles.switch_persistent('prod')
    profiles.switch_persistent('default')
    return conf.x