def use_survives_with(profiles):
    conf = ProfileConfig(profiles)
    conf.switch_to('prod')
    with conf.with_profile('default'):
        pass
    return conf.x