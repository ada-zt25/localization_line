def double_use_persistent(profiles):
    config = Config()
    profiles.load(config, 'prod')
    config.set_profile('default')
    return config.x