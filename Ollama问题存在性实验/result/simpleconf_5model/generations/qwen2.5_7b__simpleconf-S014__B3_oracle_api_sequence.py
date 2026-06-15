def with_profile_keeps_current(config):
    config.use_profile('prod')
    with config.with_profile('default'):
        pass
    return config.current_profile()