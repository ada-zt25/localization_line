def use_survives_with(profiles):
    conf = profiles.load('prod')
    with profiles.with_profile('default'):
        pass
    return conf.x