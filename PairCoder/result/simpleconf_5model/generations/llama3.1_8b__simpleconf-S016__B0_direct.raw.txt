def use_survives_with(profiles):
    config = Config()
    config.load(profiles['prod'])
    with ProfileConfig(config, 'prod'):
        with_profile('default')(config)
    return config.x