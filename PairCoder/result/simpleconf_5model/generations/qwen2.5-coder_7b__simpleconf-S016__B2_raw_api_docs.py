def use_survives_with(profiles):
    conf = ProfileConfig(profiles)
    use_profile(conf, 'prod')
    with with_profile(conf, 'default'):
        pass
    return conf.x