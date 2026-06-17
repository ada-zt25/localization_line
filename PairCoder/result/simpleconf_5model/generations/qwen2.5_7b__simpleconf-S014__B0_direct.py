def with_profile_keeps_current(config):
    config.with_profile('prod')
    with config.with_profile('default'):
        pass
    return config.active_profile_name