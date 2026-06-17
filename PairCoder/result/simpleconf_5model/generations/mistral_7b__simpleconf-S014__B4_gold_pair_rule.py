def with_profile_keeps_current(profiles):
    # Load ProfileConfig with the given profiles, using 'default' as base
    config = ProfileConfig.load(profiles, base='default')

    # Switch to 'prod' persistently
    config.use_profile(config, 'prod')

    # Enter a temporary with_profile('default') context
    with config.with_profile(config, 'default'):
        pass

    # Exit the context and return the active profile name (which should still be 'prod')
    return config.current_profile(config)