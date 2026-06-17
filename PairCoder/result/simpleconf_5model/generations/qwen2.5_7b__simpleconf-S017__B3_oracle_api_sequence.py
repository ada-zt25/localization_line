def double_use_persistent(profiles):
    conf = profiles.load('default')
    profiles.set_p persistent('prod', conf)
    profiles.set_p persistent('default', conf)
    return conf.x