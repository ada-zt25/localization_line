def use_survives_with(profiles):
    conf = Config()
    conf.load(profiles['prod'])
    with profiles.with_profile('default'):
        pass
    return conf.x